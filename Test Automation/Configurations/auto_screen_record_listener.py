import os
import configparser
from datetime import datetime
from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn
from Keywords.appium_keywords import appium_keywords


class AutoScreenRecordingListener:
    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self):
        self.appium_kw = appium_keywords()
        self.context = {}

        # --------------------------------------------------
        # Load configurations.ini
        # --------------------------------------------------
        cfg_path = os.path.join(
            os.path.dirname(__file__),
            "configurations.ini"
        )

        config = configparser.ConfigParser()
        config.read(cfg_path)

        self.enable_screen_recording = (
            config.get("DEFAULT", "enable_screen_recording", fallback="No")
            .strip().lower()
        )

        self.enable_execution_logs = (
            config.get("DEFAULT", "enable_execution_logs", fallback="No")
            .strip().lower()
        )

        logger.info(
            f"📘 Listener config | "
            f"ScreenRecording={self.enable_screen_recording}, "
            f"ExecutionLogs={self.enable_execution_logs}"
        )

    # ------------------------------------------------------------------
    # TEST START
    # ------------------------------------------------------------------
    def start_test(self, test, result):
        try:
            bi = BuiltIn()

            # -------- Resolve DUTs --------
            duts_value = bi.get_variable_value("${DUTS}", default=None)
            if duts_value:
                dut_list = [d.strip() for d in duts_value.split(",") if d.strip()]
            else:
                dut = bi.get_variable_value("${DUT}", default=None)
                if not dut:
                    logger.warn("⚠️ ${DUT}/${DUTS} not defined. Skipping recording.")
                    return
                dut_list = [dut]

            output_dir = bi.get_variable_value("${OUTPUT DIR}")
            videos_dir = os.path.join(output_dir, "videos")
            logs_dir = os.path.join(output_dir, "execution_logs")

            os.makedirs(videos_dir, exist_ok=True)
            os.makedirs(logs_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_test_name = test.name.replace(" ", "_")

            log_path = os.path.join(
                logs_dir,
                f"{timestamp}_{safe_test_name}.log"
            )

            record_video = self.enable_screen_recording in ("yes", "always")
            record_log = self.enable_execution_logs in ("yes", "always")

            self.context[test.name] = {
                "duts": {},
                "log_path": log_path,
                "start_time": datetime.now(),
                "record_video": record_video,
                "record_log": record_log
            }

            # -------- Create execution log (if enabled) --------
            if record_log:
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write(f"Test Name   : {test.name}\n")
                    f.write(f"DUTs        : {', '.join(dut_list)}\n")
                    f.write("Status      : RUNNING\n")
                    f.write(f"Start Time  : {self.context[test.name]['start_time']}\n")
                    f.write("\n--- Execution Timeline ---\n")

            # -------- Start recordings --------
            if record_video:
                for dut in dut_list:
                    video_path = os.path.join(
                        videos_dir,
                        f"{dut}_{timestamp}_{safe_test_name}.mp4"
                    )

                    self.context[test.name]["duts"][dut] = {
                        "video_path": video_path
                    }

                    logger.info(f"🎬 Starting recording | DUT={dut}")
                    self.appium_kw.start_screen_recording(
                        dut_name=dut,
                        test_name=test.name
                    )

        except Exception as e:
            logger.warn(f"⚠️ Failed to start recording: {e}")

    # ------------------------------------------------------------------
    # TEST END
    # ------------------------------------------------------------------
    def end_test(self, test, result):
        ctx = self.context.get(test.name)
        if not ctx:
            return

        try:
            failed = result.status == "FAIL"

            # -------- Stop recordings only when needed --------
            if ctx["record_video"] and (
                self.enable_screen_recording == "always"
                or (self.enable_screen_recording == "yes" and failed)
            ):
                for dut, dut_ctx in ctx["duts"].items():
                    self.appium_kw.stop_screen_recording(
                        dut_name=dut,
                        local_video_path=dut_ctx["video_path"]
                    )

            # -------- Finalize log --------
            # ----------------- Finalize execution log (if enabled) -----------------
            if ctx["record_log"] and (
                self.enable_execution_logs == "always"
                or (self.enable_execution_logs == "yes" and failed)
            ):
                end_time = datetime.now()
                duration = end_time - ctx["start_time"]

                with open(ctx["log_path"], "a", encoding="utf-8") as f:
                    f.write("\n--- Summary ---\n")
                    f.write(f"Status      : {result.status}\n")
                    f.write(f"End Time    : {end_time}\n")
                    f.write(f"Duration    : {duration}\n")

            # ----------------- ALWAYS embed artifacts if ANY enabled -----------------
            if (
                self.enable_screen_recording in ("always", "yes")
                or self.enable_execution_logs in ("always", "yes")
            ):
                self._embed_artifacts(ctx, result.status)

        except Exception as e:
            logger.warn(f"⚠️ Failed to stop recording: {e}")

    # ------------------------------------------------------------------
    # KEYWORDS
    # ------------------------------------------------------------------
    def start_keyword(self, data, result):
        self._write_log(f"▶ KEYWORD START: {data.name}")

    def end_keyword(self, data, result):
        symbol = "✔" if result.status == "PASS" else "✘"
        self._write_log(f"{symbol} KEYWORD END: {data.name} ({result.status})")

    def log_message(self, message):
        self._write_log(f"{message.level}: {message.message.strip()}")

    def _write_log(self, line):
        try:
            bi = BuiltIn()
            test_name = bi.get_variable_value("${TEST NAME}", default=None)
            if not test_name or test_name not in self.context:
                return

            if not self.context[test_name]["record_log"]:
                return

            ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            with open(self.context[test_name]["log_path"], "a", encoding="utf-8") as f:
                f.write(f"[{ts}] {line}\n")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # EMBED VIDEO + LOG IN REPORT
    # ------------------------------------------------------------------
    def _embed_artifacts(self, ctx, status):
        output_dir = BuiltIn().get_variable_value("${OUTPUT DIR}")

        html = "<details style='margin:15px 0'>"
        html += "<summary><b>🎬 Screen Recordings & Execution Log</b></summary>"

        # -------- Videos --------
        if self.enable_screen_recording in ("always", "yes"):
            for dut, dut_ctx in ctx["duts"].items():
                video_rel = os.path.relpath(
                    dut_ctx["video_path"], output_dir
                ).replace("\\", "/")

                html += f"""
                <div style="margin-top:10px">
                    <b>{dut}</b><br>
                    <video controls style="max-width:600px; max-height:400px;">
                        <source src="{video_rel}" type="video/mp4">
                    </video><br>
                    <a href="{video_rel}" target="_blank">⬇️ Download video</a>
                </div>
                <hr>
                """

        # -------- Log --------
        if self.enable_execution_logs in ("always", "yes"):
            log_rel = os.path.relpath(ctx["log_path"], output_dir).replace("\\", "/")
            html += f"""
            <b>📄 Execution Log</b><br>
            <a href="{log_rel}" target="_blank">⬇️ Download execution log</a>
            """

        html += "</details>"

        logger.info(html, html=True)


# import os
# from datetime import datetime
# from robot.api import logger
# from robot.libraries.BuiltIn import BuiltIn
# from Keywords.appium_keywords import appium_keywords


# class AutoScreenRecordingListener:
#     ROBOT_LISTENER_API_VERSION = 3

#     def __init__(self):
#         self.appium_kw = appium_keywords()
#         self.context = {}

#     # ------------------------------------------------------------------
#     # TEST START
#     # ------------------------------------------------------------------
#     def start_test(self, test, result):
#         try:
#             bi = BuiltIn()

#             duts_value = bi.get_variable_value("${DUTS}", default=None)
#             if duts_value:
#                 dut_list = [d.strip() for d in duts_value.split(",") if d.strip()]
#             else:
#                 dut = bi.get_variable_value("${DUT}", default=None)
#                 if not dut:
#                     logger.warn("⚠️ ${DUT}/${DUTS} not defined. Skipping recording.")
#                     return
#                 dut_list = [dut]

#             output_dir = bi.get_variable_value("${OUTPUT DIR}")
#             videos_dir = os.path.join(output_dir, "videos")
#             logs_dir = os.path.join(output_dir, "execution_logs")

#             os.makedirs(videos_dir, exist_ok=True)
#             os.makedirs(logs_dir, exist_ok=True)

#             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#             safe_test_name = test.name.replace(" ", "_")

#             log_path = os.path.join(
#                 logs_dir,
#                 f"{timestamp}_{safe_test_name}.log"
#             )

#             self.context[test.name] = {
#                 "log_path": log_path,
#                 "start_time": datetime.now(),
#                 "duts": {}
#             }

#             # Create single execution log
#             with open(log_path, "w", encoding="utf-8") as f:
#                 f.write(f"Test Name   : {test.name}\n")
#                 f.write(f"DUTs        : {', '.join(dut_list)}\n")
#                 f.write("Status      : RUNNING\n")
#                 f.write(f"Start Time  : {self.context[test.name]['start_time']}\n")
#                 f.write("\n--- Execution Timeline ---\n")

#             for dut in dut_list:
#                 video_path = os.path.join(
#                     videos_dir,
#                     f"{dut}_{timestamp}_{safe_test_name}.mp4"
#                 )

#                 self.context[test.name]["duts"][dut] = {
#                     "video_path": video_path
#                 }

#                 logger.info(f"🎬 Starting recording | DUT={dut}")
#                 self.appium_kw.start_screen_recording(dut_name=dut, test_name=test.name)

#         except Exception as e:
#             logger.warn(f"⚠️ Failed to start recording: {e}")

#     # ------------------------------------------------------------------
#     # TEST END
#     # ------------------------------------------------------------------
#     def end_test(self, test, result):
#         ctx = self.context.get(test.name)
#         if not ctx:
#             return

#         try:
#             for dut, dut_ctx in ctx["duts"].items():
#                 self.appium_kw.stop_screen_recording(
#                     dut_name=dut,
#                     local_video_path=dut_ctx["video_path"]
#                 )

#             end_time = datetime.now()
#             duration = end_time - ctx["start_time"]

#             with open(ctx["log_path"], "a", encoding="utf-8") as f:
#                 f.write("\n--- Summary ---\n")
#                 f.write(f"Status      : {result.status}\n")
#                 f.write(f"End Time    : {end_time}\n")
#                 f.write(f"Duration    : {duration}\n")

#             self._embed_artifacts(ctx, result.status)

#         except Exception as e:
#             logger.warn(f"⚠️ Failed to stop recording: {e}")

#     # ------------------------------------------------------------------
#     # KEYWORDS
#     # ------------------------------------------------------------------
#     def start_keyword(self, data, result):
#         self._write_log(f"▶ KEYWORD START: {data.name}")

#     def end_keyword(self, data, result):
#         symbol = "✔" if result.status == "PASS" else "✘"
#         self._write_log(f"{symbol} KEYWORD END: {data.name} ({result.status})")

#     def log_message(self, message):
#         self._write_log(f"{message.level}: {message.message.strip()}")

#     def _write_log(self, line):
#         try:
#             bi = BuiltIn()
#             test_name = bi.get_variable_value("${TEST NAME}", default=None)
#             if not test_name or test_name not in self.context:
#                 return

#             ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
#             with open(self.context[test_name]["log_path"], "a", encoding="utf-8") as f:
#                 f.write(f"[{ts}] {line}\n")
#         except Exception:
#             pass

#     # ------------------------------------------------------------------
#     # EMBED REPORT
#     # ------------------------------------------------------------------
#     def _embed_artifacts(self, ctx, status):
#         output_dir = BuiltIn().get_variable_value("${OUTPUT DIR}")
#         log_rel = os.path.relpath(ctx["log_path"], output_dir).replace("\\", "/")

#         html = "<details style='margin:15px 0'>"
#         html += "<summary><b>🎬 Screen Recordings & Execution Log</b></summary>"

#         for dut, dut_ctx in ctx["duts"].items():
#             video_rel = os.path.relpath(dut_ctx["video_path"], output_dir).replace("\\", "/")
#             html += f"""
#             <div style="margin-top:10px">
#                 <b>{dut}</b><br>
#                 <video controls style="max-width:600px; max-height:400px;">
#                     <source src="{video_rel}" type="video/mp4">
#                 </video><br>
#                 <a href="{video_rel}" target="_blank">⬇️ Download video</a>
#             </div>
#             <hr>
#             """

#         html += f"""
#         <b>📄 Execution Log</b><br>
#         <a href="{log_rel}" target="_blank">⬇️ Download execution log</a>
#         </details>
#         """

#         logger.info(html, html=True)


