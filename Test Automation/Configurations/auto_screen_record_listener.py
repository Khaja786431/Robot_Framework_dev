import os
import csv
import json
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

        # -------- Summary storage --------
        self.summary_rows = []
        self.summary_rendered = False
        self.total_pass = 0
        self.total_fail = 0
        self.total_skip = 0

        # -------- Load configurations.ini --------
        cfg_path = os.path.join(os.path.dirname(__file__), "configurations.ini")
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
            f"ExecutionLogs={self.enable_execution_logs}",
        )

    # ------------------------------------------------------------------
    # TEST START
    # ------------------------------------------------------------------
    def start_test(self, test, result):
        try:
            bi = BuiltIn()

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
            log_path = os.path.join(logs_dir, f"{timestamp}_{safe_test_name}.log")

            record_video = self.enable_screen_recording in ("yes", "always")
            record_log = self.enable_execution_logs in ("yes", "always")

            self.context[test.name] = {
                "duts": {},
                "log_path": log_path,
                "start_time": datetime.now(),
                "record_video": record_video,
                "record_log": record_log,
            }

            if record_log:
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write(f"Test Name   : {test.name}\n")
                    f.write(f"DUTs        : {', '.join(dut_list)}\n")
                    f.write("Status      : RUNNING\n")
                    f.write(f"Start Time  : {self.context[test.name]['start_time']}\n")
                    f.write("\n--- Execution Timeline ---\n")

            if record_video:
                for dut in dut_list:
                    video_path = os.path.join(
                        videos_dir, f"{dut}_{timestamp}_{safe_test_name}.mp4"
                    )
                    self.context[test.name]["duts"][dut] = {
                        "video_path": video_path
                    }
                    logger.info(f"🎬 Starting recording | DUT={dut}")
                    self.appium_kw.start_screen_recording(dut, test.name)

        except Exception as e:
            logger.warn(f"⚠️ Failed to start recording: {e}")

    # ------------------------------------------------------------------
    # TEST END
    # ------------------------------------------------------------------
    def end_test(self, test, result):
        ctx = self.context.get(test.name)
        if not ctx:
            return

        failed = result.status == "FAIL"

        # -------- Stop recordings --------
        if ctx["record_video"] and (
            self.enable_screen_recording == "always"
            or (self.enable_screen_recording == "yes" and failed)
        ):
            for dut, dut_ctx in ctx["duts"].items():
                self.appium_kw.stop_screen_recording(
                    dut, dut_ctx["video_path"]
                )

        # -------- Finalize log --------
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

        # -------- Embed artifacts --------
        if (
            self.enable_screen_recording in ("always", "yes")
            or self.enable_execution_logs in ("always", "yes")
        ):
            self._embed_artifacts(ctx)

        # -------- Update summary --------
        duration = datetime.now() - ctx["start_time"]
        duration_str = str(duration).split(".")[0]
        dut_names = ", ".join(ctx["duts"].keys())

        if result.status == "PASS":
            self.total_pass += 1
            row_class = "row-pass"
        elif result.status == "FAIL":
            self.total_fail += 1
            row_class = "row-fail"
        else:
            self.total_skip += 1
            row_class = "row-skip"

        self.summary_rows.append({
            "test": test.name,
            "anchor": test.name.replace(" ", "_"),
            "duts": dut_names,
            "status": result.status,
            "duration": duration_str,
            "row_class": row_class,
            "video": self.enable_screen_recording in ("yes", "always"),
            "log": self.enable_execution_logs in ("yes", "always"),
        })

        self._render_summary_table()
        self._export_summary()

    # ------------------------------------------------------------------
    # SUMMARY TABLE (TOP OF REPORT)
    # ------------------------------------------------------------------
    def _render_summary_table(self):
        if self.summary_rendered:
            return

        rows_html = ""
        for r in self.summary_rows:
            rows_html += f"""
            <tr class="{r['row_class']}">
            <td><a href="#test-{r['anchor']}">{r['test']}</a></td>
            <td>{r['duts']}</td>
            <td>{r['status']}</td>
            <td>{r['duration']}</td>
            <td style="text-align:center">{'🎬' if r['video'] else '—'}</td>
            <td style="text-align:center">{'📄' if r['log'] else '—'}</td>
            </tr>
            """

        totals_row = f"""
        <tr style="font-weight:bold; background:#f5f5f5">
        <td colspan="2">TOTAL</td>
        <td>✅ {self.total_pass} | ❌ {self.total_fail} | ⚠️ {self.total_skip}</td>
        <td colspan="3"></td>
        </tr>
        """

        # CSV / JSON files are in OUTPUT DIR
        csv_rel = "execution_summary.csv"
        json_rel = "execution_summary.json"

        html = f"""
        <div id="execution-summary-container">
        <style>
        .row-pass {{ background:#e6ffed; }}
        .row-fail {{ background:#ffe6e6; }}
        .row-skip {{ background:#fff8e6; }}
        tr:hover {{ background:#eaf2ff; }}
        </style>

        <h2>📊 Execution Summary</h2>

        <table border="1" cellpadding="6" cellspacing="0"
            style="border-collapse:collapse; width:100%">
        <thead style="background:#f0f0f0">
            <tr>
            <th>Test Name</th>
            <th>DUT(s)</th>
            <th>Status</th>
            <th>Duration</th>
            <th>Video</th>
            <th>Log</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
            {totals_row}
        </tbody>
        </table>

        <div style="margin-top:10px">
        <b>📦 Export Summary</b><br>
        <a href="{csv_rel}" target="_blank">⬇️ Download CSV</a><br>
        <a href="{json_rel}" target="_blank">⬇️ Download JSON</a>
        </div>
        </div>

        <script>
        (function() {{
            var s = document.getElementById("execution-summary-container");
            document.body.insertBefore(s, document.body.firstChild);
        }})();
        </script>
        <hr>
        """

        logger.info(html, html=True)
        self.summary_rendered = True


    # ------------------------------------------------------------------
    # EXPORT SUMMARY
    # ------------------------------------------------------------------
    def _export_summary(self):
        if not self.summary_rows:
            return

        output_dir = BuiltIn().get_variable_value("${OUTPUT DIR}")
        csv_path = os.path.join(output_dir, "execution_summary.csv")
        json_path = os.path.join(output_dir, "execution_summary.json")

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["test", "duts", "status", "duration", "video", "log"]
            )
            writer.writeheader()
            for r in self.summary_rows:
                writer.writerow({
                    "test": r["test"],
                    "duts": r["duts"],
                    "status": r["status"],
                    "duration": r["duration"],
                    "video": r["video"],
                    "log": r["log"],
                })

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.summary_rows, f, indent=2)

    # ------------------------------------------------------------------
    # KEYWORD / LOGGER LOGGING
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
    # EMBED ARTIFACTS
    # ------------------------------------------------------------------
    def _embed_artifacts(self, ctx):
        output_dir = BuiltIn().get_variable_value("${OUTPUT DIR}")

        html = "<details style='margin:15px 0'>"
        html += "<summary><b>🎬 Screen Recordings & Execution Log</b></summary>"

        if self.enable_screen_recording in ("always", "yes"):
            for dut, dut_ctx in ctx["duts"].items():
                video_rel = os.path.relpath(
                    dut_ctx["video_path"], output_dir
                ).replace("\\", "/")
                html += f"""
                <div>
                  <b>{dut}</b><br>
                  <video controls style="max-width:600px; max-height:400px;">
                    <source src="{video_rel}" type="video/mp4">
                  </video><br>
                  <a href="{video_rel}">⬇️ Download video</a>
                </div><hr>
                """

        if self.enable_execution_logs in ("always", "yes"):
            log_rel = os.path.relpath(ctx["log_path"], output_dir).replace("\\", "/")
            html += f"""
            <b>📄 Execution Log</b><br>
            <a href="{log_rel}">⬇️ Download execution log</a>
            """

        html += "</details>"
        logger.info(html, html=True)
