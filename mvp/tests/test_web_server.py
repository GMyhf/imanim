"""创空间部署开关：MVP_GENERATE_DISABLED=1 时在线生成必须关闭（容器里没有配好的模型网关密钥/网络）。

这个开关是部署侧唯一的"别在演示当场跑一条必挂的任务"保险，所以它只能靠环境变量生效、
并且必须在**创建任务之前**拦下——否则前端会看到一个永远 running 的僵尸作业。
"""
import importlib
import io
import json
import os
import sys
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "web"))
server = importlib.import_module("server")  # 供 FakeHandler 类定义绑定；用例内一律用 load() 的副本


def load(disabled: bool):
    if disabled:
        os.environ["MVP_GENERATE_DISABLED"] = "1"
    else:
        os.environ.pop("MVP_GENERATE_DISABLED", None)
    return importlib.reload(importlib.import_module("server"))


class TestGenerateDisabled(unittest.TestCase):
    def test_guard_is_off_by_default(self):
        self.assertFalse(load(False).GENERATE_DISABLED)

    def test_both_entry_points_refuse_before_creating_a_job(self):
        server = load(True)
        self.assertTrue(server.GENERATE_DISABLED)
        jobs_dir = server.JOBS_DIR
        before = set(jobs_dir.glob("*")) if jobs_dir.is_dir() else set()
        for call in (lambda: server.start_generate({}, "fullhd"),
                     lambda: server.start_regenerate("out:nothing", [{}], "fullhd")):
            with self.assertRaises(ValueError) as ctx:
                call()
            self.assertIn("已关闭", str(ctx.exception))
        self.assertEqual(set(jobs_dir.glob("*")) if jobs_dir.is_dir() else set(), before,
                         "拦截发生在建任务之前，不该留下作业目录")

    def test_message_tells_the_visitor_what_still_works(self):
        """画廊与文档仍然可用，提示里必须说清"这里能干什么"，不能只丢一句"失败"。"""
        msg = load(True).GENERATE_DISABLED_MSG
        self.assertIn("画廊", msg)
        self.assertIn("README", msg)


class TestFeedback(unittest.TestCase):
    """问题反馈：本地演示无账号，只落盘本机文件；GENERATE_DISABLED 部署下仍可收。"""

    def _tmp_dir(self, monkeypatch_fb):
        import tempfile
        d = tempfile.mkdtemp(prefix="fb_test_")
        self.addCleanup(lambda: __import__("shutil").rmtree(d, ignore_errors=True))
        server = load(False)
        server.FEEDBACK_DIR = Path(d)
        return server

    def test_valid_feedback_is_written(self):
        server = self._tmp_dir(None)
        res = server.submit_feedback({"type": "bug", "text": "第3镜字幕错位", "contact": ""})
        self.assertTrue(res.get("ok"))
        files = list(server.FEEDBACK_DIR.glob("*.json"))
        self.assertEqual(len(files), 1)
        data = json.loads(files[0].read_text(encoding="utf-8"))
        self.assertEqual(data["type"], "bug")
        self.assertEqual(data["text"], "第3镜字幕错位")

    def test_invalid_payloads_are_rejected(self):
        server = self._tmp_dir(None)
        for bad in ({"type": "bug", "text": ""},
                    {"type": "hack", "text": "x"},
                    {"type": "bug", "text": "x" * 5001},
                    {"type": "bug", "text": "x", "contact": "y" * 201}):
            with self.assertRaises(ValueError):
                server.submit_feedback(bad)
        self.assertEqual(list(server.FEEDBACK_DIR.glob("*.json")), [])

    def test_feedback_works_when_generate_is_disabled(self):
        server = load(True)
        import tempfile
        d = tempfile.mkdtemp(prefix="fb_test_")
        self.addCleanup(lambda: __import__("shutil").rmtree(d, ignore_errors=True))
        server.FEEDBACK_DIR = Path(d)
        res = server.submit_feedback({"type": "suggestion", "text": "想要下载按钮", "contact": "a@b.c"})
        self.assertTrue(res.get("ok"))


class FakeHandler(server.Handler):
    """不建 socket 的最小 Handler：只复用 send_file / api_* 这些写 wfile 的方法。"""

    def __init__(self, headers=None):
        self.headers = Message()
        for k, v in (headers or {}).items():
            self.headers[k] = v
        self.wfile = io.BytesIO()
        self._headers_buffer = []
        self.head = False
        self.requestline = "GET / HTTP/1.1"  # log_request 在调 log_message 前就会读它
        self.request_version = "HTTP/1.1"    # send_response_only 判 HTTP/0.9 分支用

    def log_message(self, fmt, *args):  # 测试里不写访问日志
        pass


class TestRunDirFor(unittest.TestCase):
    """run_dir_for 只接受单层 ASCII 目录名：点号段是唯一的穿越通道，必须单独挡。"""

    def test_dot_and_dotdot_names_are_rejected(self):
        srv = load(False)
        for key in ("out:.", "out:..", "job:.", "job:.."):
            self.assertIsNone(srv.run_dir_for(key), f"{key} 不能解析出上级目录")

    def test_bad_root_or_nested_names_are_rejected(self):
        srv = load(False)
        for key in ("etc:passwd", "out:a/b", "out:a\\b", "out:中文名", "out:", "out:" + "x" * 65):
            self.assertIsNone(srv.run_dir_for(key), key)

    def test_normal_names_resolve_inside_the_roots(self):
        srv = load(False)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out, jobs = root / "out", root / "jobs"
            (out / "demo").mkdir(parents=True)
            (jobs / "g1").mkdir(parents=True)
            (jobs / "g2" / "run").mkdir(parents=True)
            with mock.patch.object(srv, "OUT_DIR", out), mock.patch.object(srv, "JOBS_DIR", jobs):
                self.assertEqual(srv.run_dir_for("out:demo"), out / "demo")
                self.assertIsNone(srv.run_dir_for("out:missing"))
                self.assertEqual(srv.run_dir_for("job:g1"), jobs / "g1")   # 无 run 子目录退回 job 目录
                self.assertEqual(srv.run_dir_for("job:g2"), jobs / "g2" / "run")
                self.assertIsNone(srv.run_dir_for("job:missing"))


class TestSendFileRange(unittest.TestCase):
    """send_file 的 Range 语义（含已修的 bytes=-N 后缀区间 bug）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.file = Path(self._tmp.name) / "data.bin"
        self.file.write_bytes(b"0123456789")  # 10 字节

    def serve(self, rng=None):
        h = FakeHandler({"Range": rng} if rng else {})
        h.send_file(self.file)
        raw = h.wfile.getvalue()
        head, body = raw.split(b"\r\n\r\n", 1)
        return head, body

    def test_no_range_serves_the_whole_file(self):
        head, body = self.serve()
        self.assertIn(b" 200 ", head.split(b"\r\n")[0])
        self.assertEqual(body, b"0123456789")

    def test_plain_range_is_inclusive(self):
        head, body = self.serve("bytes=2-5")
        self.assertEqual(body, b"2345")
        self.assertIn(b"Content-Range: bytes 2-5/10", head)

    def test_open_ended_range_runs_to_the_end(self):
        head, body = self.serve("bytes=7-")
        self.assertEqual(body, b"789")
        self.assertIn(b"Content-Range: bytes 7-9/10", head)

    def test_suffix_range_serves_the_last_n_bytes(self):
        """BUG（已修）：bytes=-3 曾被解析成 0..3，把文件开头当结尾发出去。"""
        head, body = self.serve("bytes=-3")
        self.assertEqual(body, b"789")
        self.assertIn(b"Content-Range: bytes 7-9/10", head)

    def test_suffix_range_larger_than_the_file_clamps_to_whole(self):
        head, body = self.serve("bytes=-999")
        self.assertEqual(body, b"0123456789")
        self.assertNotIn(b"Content-Range", head)

    def test_range_beyond_eof_is_416(self):
        head, body = self.serve("bytes=50-")
        self.assertIn(b"416", head.split(b"\r\n")[0])
        self.assertEqual(body, b"")

    def test_inverted_range_is_416(self):
        head, body = self.serve("bytes=5-2")
        self.assertIn(b"416", head.split(b"\r\n")[0])


class TestApiGenerateMainPath(unittest.TestCase):
    """api_generate 的主路径：契约校验 → 防幻觉闸门 → 建任务（子进程生成靠 mock，不真跑）。"""

    def call(self, payload, encoding="utf-8"):
        srv = load(False)
        h = FakeHandler()
        raw = json.dumps(payload, ensure_ascii=False).encode(encoding)
        h.headers["Content-Length"] = str(len(raw))
        h.rfile = io.BytesIO(raw)
        return srv, h

    def respond(self, srv, h):
        srv.Handler.api_generate(h)
        head, body = h.wfile.getvalue().split(b"\r\n\r\n", 1)
        return head.split(b"\r\n")[0], json.loads(body.decode("utf-8"))

    def brief(self, **over):
        base = {"subject": "physics", "grade": "H1", "topic": "加速度",
                "target_seconds": 120, "style": "clean", "resolution": "1920x1080"}
        base.update(over)
        return base

    def test_happy_path_creates_a_job_and_normalizes_the_topic(self):
        srv, h = self.call(self.brief(quality="draft"))
        with mock.patch.object(srv, "start_generate", return_value="g1") as start:
            line, out = self.respond(srv, h)
        self.assertIn(b"200", line)
        self.assertEqual(out["job"], "g1")
        self.assertEqual(out["knowledge"]["id"], "kp.physics.acceleration")
        self.assertTrue(start.called)
        self.assertNotIn("quality", start.call_args.args[0], "运行参数不许混进 Brief 契约")

    def test_unknown_topic_is_rejected_with_candidates(self):
        srv, h = self.call(self.brief(topic="不存在的东西"))
        line, out = self.respond(srv, h)
        self.assertIn(b"400", line)
        self.assertIn("编造知识点", out["error"])
        self.assertIn("加速度", out["candidates"])

    def test_invalid_brief_contract_is_400_with_findings(self):
        srv, h = self.call(self.brief(target_seconds=10))
        line, out = self.respond(srv, h)
        self.assertIn(b"400", line)
        self.assertTrue(out["findings"])
        self.assertIn("target_seconds", "".join(out["findings"]))

    def test_gbk_body_is_decoded(self):
        """curl/PowerShell 按 GBK 送中文是这台机器的常态，read_body 必须兜住。"""
        srv, h = self.call(self.brief(quality="draft"), encoding="cp936")
        with mock.patch.object(srv, "start_generate", return_value="g1"):
            line, out = self.respond(srv, h)
        self.assertEqual(out["knowledge"]["id"], "kp.physics.acceleration")


class TestApiRegenerateMainPath(unittest.TestCase):
    def call(self, payload):
        srv = load(False)
        h = FakeHandler()
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        h.headers["Content-Length"] = str(len(raw))
        h.rfile = io.BytesIO(raw)
        return srv, h

    def respond(self, srv, h):
        srv.Handler.api_regenerate(h)
        head, body = h.wfile.getvalue().split(b"\r\n\r\n", 1)
        return head.split(b"\r\n")[0], json.loads(body.decode("utf-8"))

    def test_happy_path_spawns_a_render_job(self):
        srv, h = self.call({"source_key": "out:whatever",
                            "shots": [{"index": 0, "narration": "改过的口播"}],
                            "quality": "draft"})
        with mock.patch.object(srv, "start_regenerate", return_value="r1") as start:
            line, out = self.respond(srv, h)
        self.assertIn(b"200", line)
        self.assertEqual(out["job"], "r1")
        self.assertEqual(start.call_args.args[0], "out:whatever")
        self.assertEqual(start.call_args.args[2], "draft")

    def test_empty_shots_are_rejected(self):
        srv, h = self.call({"source_key": "out:whatever", "shots": []})
        line, out = self.respond(srv, h)
        self.assertIn(b"400", line)
        self.assertIn("shots", out["error"])

    def test_unknown_source_key_is_a_clean_400_not_a_500(self):
        srv, h = self.call({"source_key": "out:no-such-run-abc", "shots": [{"index": 0}]})
        line, out = self.respond(srv, h)
        self.assertIn(b"400", line)
        self.assertIn("plan.json", out["error"])


if __name__ == "__main__":
    unittest.main()
