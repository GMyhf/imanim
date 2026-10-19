/* 澄象 MVP · 前端逻辑
 * 动线（与竞品一致）：输入 → 分类 → 生成 → 进度 → 成片 + 分镜可改 → 下方作品墙。
 * 差异点：输入是结构化契约（Spec_Product 第 2 节）；过程有阶段名与耗时；Plan 可见可编辑可重出片。
 */
"use strict";

const $ = (sel) => document.querySelector(sel);
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
};

const state = {
  meta: null,          // /api/topics 的枚举
  topics: [],
  job: null,
  poll: null,
  tick: null,
  currentKey: null,    // 当前结果区对应的 run（job:xxx 或 out:xxx），重出片时作为源
  plan: null,
  busy: false,
};

const DEFAULTS = { subject: "physics", grade: "H1", seconds: "120", style: "clean", quality: "draft" };

/* 错误人话映射（SubTask 63）：结论用人话说，原始错误文本保留在 details 折叠里，不吞信息。 */
const NET_MSG = "无法连接到渲染服务：服务可能没有启动，或中途退出了。请确认服务正在运行后刷新页面。";
const DISABLED_MSG = "当前部署已关闭在线生成（409）：这里只浏览已生成的作品墙、分镜脚本与技术文档。";
const JOB_FAIL_MSG = "生成失败：作业在执行中出错，未产出成片。原始错误见下方详情。";
const GATE_FAIL_MSG = "生成被静态监督闸门打回：分镜未通过检查，未烧录半成品。可在下方修改分镜后重出片。";

/* 本机浏览器记忆上次的身份/风格偏好（SubTask 51）：只用 localStorage，不发后端、不建账号，
 * 换设备或清缓存即丢失，与 Spec_Product.txt「不做账号」的边界不冲突。 */
const PREF_KEY = "chengxiang.prefs.v1";
function loadPrefs() {
  try { return JSON.parse(localStorage.getItem(PREF_KEY)) || {}; } catch (e) { return {}; }
}
function savePrefs(patch) {
  try { localStorage.setItem(PREF_KEY, JSON.stringify({ ...loadPrefs(), ...patch })); } catch (e) { /* 隐私模式等场景下静默跳过 */ }
}

/* ------------------------------------------------------------------ 枚举与表单 */
async function loadTopics() {
  let r, d;
  try {
    r = await fetch("/api/topics");
    d = await r.json();
  } catch (e) {
    return showError($("#briefError"), NET_MSG, "无法连接服务：" + e);
  }
  if (!r.ok) return showError($("#briefError"), d.error || "知识点库读取失败");
  state.meta = d;
  state.topics = d.topics || [];
  /* 状态诚实：服务端 generate_disabled=1（创空间默认）时，表单里一眼说明「只展映、生成未开放」。
   * 文案用服务端 GENERATE_DISABLED_MSG 原文，前端不特判、不伪造进度。 */
  const dis = !!d.generate_disabled;
  const note = $("#genNotice");
  if (dis) {
    note.textContent = d.generate_disabled_msg || DISABLED_MSG;
    note.hidden = false;
  } else {
    note.hidden = true;
  }
  const pref = loadPrefs();
  fill($("#fSubject"), d.subjects, pref.subject || DEFAULTS.subject);
  fill($("#fGrade"), d.grades, pref.grade || DEFAULTS.grade);
  fill($("#fStyle"), d.styles, pref.style || DEFAULTS.style);
  fill($("#fQuality"), d.qualities, pref.quality || DEFAULTS.quality);
  $("#fSeconds").append(...d.durations.map((s) => opt(String(s), s + " 秒")));
  $("#fSeconds").value = pref.seconds || DEFAULTS.seconds;
}

function fill(select, list, def) {
  select.textContent = "";
  select.append(...list.map((i) => opt(i.value, i.label)));
  if (def && list.some((i) => i.value === def)) select.value = def;
}
const opt = (value, label) => Object.assign(el("option"), { value, textContent: label });

/* ------------------------------------------------------------------ 生成 + 轮询 */
function briefFromForm() {
  return {
    subject: $("#fSubject").value,
    grade: $("#fGrade").value,
    topic: $("#fTopic").value.trim(),
    target_seconds: parseInt($("#fSeconds").value, 10),
    style: $("#fStyle").value,
    quality: $("#fQuality").value,
    narration: true,
    prior_knowledge: $("#fPrior").checked,
    raw_text: $("#fRaw").value.trim(),
  };
}

async function generate() {
  if (state.busy) return;
  const b = briefFromForm();
  if (!b.topic) return showError($("#briefError"), "请先写一个知识点");
  hideError($("#briefError"));
  const res = await post("/api/generate", b);
  if (!res) return;
  const job = res.data;
  if (res.status === 409) return showError($("#briefError"), DISABLED_MSG, job.error || "HTTP 409");
  if (job.error) {
    // Brief.validate() 的错误清单在 findings；知识点未命中的候选在 candidates。校验类错误本身就是人话，原样保留。
    let msg = job.error;
    if (job.findings && job.findings.length) msg += "\n" + job.findings.map((f) => "· " + f).join("\n");
    if (job.candidates && job.candidates.length) msg += "\n可选知识点：" + job.candidates.join("、");
    return showError($("#briefError"), msg);
  }
  startJob(job.job, "生成");
}

async function regenerate() {
  if (state.busy) return;
  if (!state.currentKey) return showError($("#planError"), "没有可修改的成片");
  const shots = [...document.querySelectorAll(".shot")].map((node) => ({
    index: Number(node.dataset.index),
    title: node.querySelector(".t-in").value.trim(),
    narration: node.querySelector(".n-in").value.trim(),
    seconds: parseFloat(node.querySelector(".s-in").value),
  }));
  hideError($("#planError"));
  const body = { source_key: state.currentKey, shots, quality: $("#fQuality").value };
  const res = await post("/api/regenerate", body);
  if (!res) return;
  const job = res.data;
  if (res.status === 409) return showError($("#planError"), DISABLED_MSG, job.error || "HTTP 409");
  if (job.error) return showError($("#planError"), job.error);
  startJob(job.job, "按修改重出片");
}

async function improve() {
  if (state.busy) return;
  if (!state.currentKey) return showError($("#improveError"), "没有可改进的成片");
  const instruction = $("#fImprove").value.trim();
  if (!instruction) return showError($("#improveError"), "请先写一句改进意见");
  hideError($("#improveError"));
  const res = await post("/api/improve", {
    source_key: state.currentKey, instruction, quality: $("#fQuality").value,
  });
  if (!res) return;
  const job = res.data;
  if (res.status === 409) return showError($("#improveError"), DISABLED_MSG, job.error || "HTTP 409");
  if (job.error) return showError($("#improveError"), job.error);
  startJob(job.job, "按改进意见重出片");
}

function startJob(jobId, kindLabel) {
  stopPolling();
  state.job = jobId;
  state.busy = true;
  setBusy(true);
  $("#progressCard").classList.remove("hidden");
  $("#jobHint").textContent = `${kindLabel} · 任务 ${jobId} · 云端生成中，用时见下方计时`;
  $("#stageList").textContent = "";
  $("#stageBar").hidden = true;
  $("#stageBarFill").style.width = "0";
  $("#stageBarFill").className = "stagebar-fill";
  $("#jobError").hidden = true;
  $("#elapsedSec").textContent = "0";
  state.tick = setInterval(() => {
    const s = $("#elapsedSec");
    s.textContent = String(Number(s.textContent) + 1);
  }, 1000);
  pollOnce();
  state.poll = setInterval(pollOnce, 2000);
}

async function pollOnce() {
  if (!state.job) return;
  let d;
  try {
    d = await (await fetch(`/api/status/${state.job}`)).json();
  } catch (e) { return; }
  if (d.error && !d.state) return finishJob(d.error);
  renderStages(d.stages || [], d.state);
  $("#elapsedSec").textContent = String(Math.round(d.elapsed || 0));
  if (d.state === "done") return finishJob(null, d);
  if (d.state === "failed") return finishJob(d.error, d);
}

/* 阶段指示条（SubTask 63）：只用 /api/status 已返回的字段（stages[].key/label/status/seconds + state），
 * 状态词固定四档：待开始 / 进行中 / 完成 / 失败（failed 由作业整体 state 映射到当时的 running 阶段）。
 * 接口没给的阶段一律显示 pending，不伪造阶段名。 */
const STAGE_STATE_TEXT = { pending: "待开始", running: "进行中", done: "完成", failed: "失败" };
function renderStages(stages, jobState) {
  const box = $("#stageList");
  box.textContent = "";
  const shown = stages.map((s) =>
    jobState === "failed" && s.status === "running" ? { ...s, status: "failed" } : s);
  const bar = $("#stageBar"), fill = $("#stageBarFill");
  if (shown.length) {
    const doneCount = shown.filter((s) => s.status === "done").length;
    bar.hidden = false;
    fill.style.width = Math.round((doneCount / shown.length) * 100) + "%";
    fill.classList.toggle("done", jobState === "done");
    fill.classList.toggle("failed", jobState === "failed");
  } else {
    bar.hidden = true;
  }
  for (const s of shown) {
    const n = el("span", "stage " + s.status);
    n.append(el("span", "", s.label));
    n.append(el("span", "stage-state", " · " + (STAGE_STATE_TEXT[s.status] || s.status)));
    if (s.seconds !== null && s.seconds !== undefined) n.append(el("span", "sec", ` ${s.seconds}s`));
    box.append(n);
  }
}

function finishJob(error, d) {
  stopPolling();
  state.busy = false;
  setBusy(false);
  if (error) {
    renderJobError(error);
    if (d && d.result && d.result.meta) showResult(d.result.meta, d.result.plan, d);
    return;
  }
  $("#jobHint").textContent = `已完成 · 任务 ${state.job}`;
  showResult(d.result.meta, d.result.plan, d);
  loadGallery();
}

/* 作业失败的人话映射：闸门打回 / 口播装不下 / 生成被禁用 / 一般失败四类；原始错误进 details 折叠。
 * 带 suggestion（GenerationError / 时长不可行）时单独亮一行"接下来怎么办"，不吞原错误。 */
function renderJobError(error) {
  const box = $("#jobError");
  const raw = typeof error === "string" ? error : JSON.stringify(error, null, 2);
  let friendly = JOB_FAIL_MSG, suggest = "";
  if (error && typeof error === "object") {
    suggest = error.suggestion || "";
    if (error.findings_raw) {
      friendly = GATE_FAIL_MSG;
    } else if (error.kind === "duration_infeasible") {
      friendly = "口播放不进目标时长，请按建议调整后重试。";
    }
  } else if (raw.includes("在线生成在当前部署里已关闭")) {
    friendly = DISABLED_MSG;
  }
  const detail = formatError(error);
  box.textContent = "";
  box.append(el("p", "err-msg", friendly));
  if (suggest) box.append(el("p", "err-suggest", suggest));
  const det = el("details", "err-raw");
  det.append(el("summary", "", "原始错误详情"));
  det.append(el("pre", "", String(detail)));
  box.append(det);
  box.hidden = false;
}

function formatError(e) {
  if (typeof e === "string") return e;
  // jobrunner 把闸门结果编成 {error, findings_raw|findings}，这里去重成一段人话
  if (e.findings_raw) return e.findings_raw.replace(/^[\u4e00-\u9fa5]+：/, "静态监督打回：\n");
  if (e.candidates) return e.error + "\n可选知识点：" + e.candidates.join("、");
  return e.error || JSON.stringify(e);
}
function stopPolling() {
  clearInterval(state.poll); clearInterval(state.tick);
  state.poll = state.tick = null;
}
function setBusy(on) {
  $("#btnGenerate").disabled = on;
  $("#btnGenerate").setAttribute("aria-busy", String(on));
  $("#btnRegenerate").disabled = on;
  $("#briefCard").toggleAttribute("aria-busy", on);
}

/* ------------------------------------------------------------------ 结果区 */
function showResult(meta, plan, d) {
  if (!meta) return;
  const card = $("#resultCard");
  card.classList.remove("hidden");
  state.currentKey = meta.key;
  state.plan = plan;

  const side = (d && d.result && d.result.sidecar) || {};
  const dur = (side.duration && side.duration.actual) || meta.seconds;
  const size = side.size_mb || meta.size_mb;
  const wall = side.wall_seconds || meta.wall_seconds;
  $("#resultMeta").textContent =
    `${labelSubject(meta.subject)} · ${meta.grade_label || meta.grade} · ${meta.topic}` +
    ` · 成片 ${dur ? dur + "s（目标 " + meta.target_seconds + "s）" : ""}` +
    `${size ? " · " + size + "MB" : ""}${wall ? " · 耗时 " + wall + "s" : ""}` +
    `${meta.source === "示例库" ? " · 来自已生成库" : ""}`;
  // 提速过就要说清楚代价（C13 产品口径）：老师看到"自然语速需 171s"才知道该放宽时长而不是怪语速。
  const ttsNote = side.tts && side.tts.note;
  $("#resultTts").textContent = ttsNote || "";
  $("#resultTts").classList.toggle("hidden", !ttsNote);

  const player = $("#player");
  const wrap = $(".player-wrap");
  if (meta.video) {
    wrap.classList.remove("hidden");
    player.src = meta.video;
    player.load();
  } else {
    wrap.classList.add("hidden");     // 被闸门打回时没有成片，只留分镜供修改
    player.removeAttribute("src");
  }

  const dl = $("#downloads");
  dl.textContent = "";
  for (const f of wanted(meta.files)) {
    const a = el("a", "dl");
    a.href = f.url + "?download=1";
    a.append(el("span", "", f.label), el("span", "sz", human(f.size)));
    dl.append(a);
  }
  renderShots(plan);
  // prefers-reduced-motion 时不做平滑滚动（CSS 侧已关动画，这里管住 JS 触发的滚动）
  const reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  card.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
}

/* 需求：final.mp4 / burned 版 / subs.srt / plan.json 四个都要能拿到（后端按角色解析真实路径） */
function wanted(files) {
  const keep = ["final", "burned", "srt", "plan", "named", "sidecar"];
  return (files || []).filter((f) => keep.includes(f.role));
}

function renderShots(plan) {
  const box = $("#shots");
  box.textContent = "";
  const shots = (plan && plan.shots) || [];
  if (!shots.length) {
    box.append(el("p", "hint", "该 run 没有 plan.json，无法编辑分镜。"));
    $("#btnRegenerate").disabled = true;
    return;
  }
  $("#btnRegenerate").disabled = false;
  // 时间轴口径由后端 /api/topics 下发（单一真源），前端不再各写常量。
  const HEAD = (state.meta && state.meta.shot_head) ?? 0.45;
  const TAIL = (state.meta && state.meta.shot_tail) ?? 0.70;
  const MIN = (state.meta && state.meta.min_shot_seconds) ?? 4;
  const ver = (plan.version || "") + (plan.hash ? " · " + plan.hash : "");
  box.append(el("p", "hint",
    `分镜 IR ${ver || "（旧版无版本/hash）"} · 镜头时长含淡入 ${HEAD}s 与淡出 ${TAIL}s 留白，`
    + `口播只占中间窗口，字幕时间是镜头内的绝对秒（从 ${HEAD}s 起，不是从 0 平铺）。`));
  for (const s of shots) {
    const card = el("div", "shot");
    card.dataset.index = s.index;

    const top = el("div", "shot-top");
    top.append(el("span", "shot-idx", "镜头 " + (s.index + 1)));
    const title = el("input", "t-in");
    title.value = s.title || "";
    title.setAttribute("aria-label", "镜头标题");
    top.append(title);
    const kinds = el("span", "shot-kinds");
    kinds.append(el("span", "", "版式原语："));
    (s.visuals || []).forEach((v) => kinds.append(el("code", "", v.kind)));
    top.append(kinds);
    card.append(top);

    const fields = el("div", "shot-fields");
    const secs = el("input", "s-in");
    secs.type = "number"; secs.step = "0.1"; secs.min = String(MIN); secs.value = s.seconds;
    fields.append(el("label", "", "镜头时长（秒，含前后留白）"), secs);
    fields.append(el("label", "", "口播文本"));
    const nar = el("textarea", "n-in");
    nar.value = s.narration || "";
    fields.append(nar);
    card.append(fields);

    // 口播窗口 = [SHOT_HEAD, seconds - SHOT_TAIL]：改口播文本或时长后重出片会重新实测语音并回填时长。
    const win = Number(s.seconds) - HEAD - TAIL;
    card.append(el("p", "hint",
      `口播窗口 ${HEAD}–${(Number(s.seconds) - TAIL).toFixed(2)}s（约 ${win > 0 ? win.toFixed(2) : 0}s 可念白）`));

    // 字幕 cue：Plan.to_dict 已给出镜头内绝对时间，这里如实展示（旧版字幕平铺 [0, seconds] 的假设已废弃）。
    const subs = s.subtitles || [];
    if (subs.length) {
      const list = el("div", "shot-subs");
      list.append(el("span", "flabel", `字幕（${subs.length} 条 · 镜头内绝对时间）`));
      for (const c of subs) {
        const line = el("div", "sub-line");
        line.append(el("code", "", `${c.start.toFixed(2)}–${c.end.toFixed(2)}s`), el("span", "", c.text));
        list.append(line);
      }
      card.append(list);
    }

    const refs = (s.kp_refs || []).join(" ／ ");
    if (refs) card.append(el("p", "shot-refs", "出处：" + refs));
    box.append(card);
  }
}

/* ------------------------------------------------------------------ 作品墙 */
async function loadGallery() {
  let r, d;
  try {
    r = await fetch("/api/gallery");
    d = await r.json();
  } catch (e) {
    $("#wallHint").textContent = "作品墙加载失败：无法连接服务，请稍后刷新重试。";
    return;
  }
  if (!r.ok || d.error) {  // 接口 5xx/4xx 时不能冒充「新作品制作中」的空态
    $("#wallHint").textContent = "作品墙加载失败：" + (d && d.error ? d.error : "HTTP " + r.status);
    return;
  }
  const items = d.items || [];
  const tabs = $("#wallTabs");
  if (tabs.children.length === 1) {
    for (const s of (state.meta ? state.meta.subjects : [{ value: "math", label: "数学" }, { value: "physics", label: "物理" }, { value: "chemistry", label: "化学" }])) {
      const b = el("button", "tab", s.label);
      b.dataset.subject = s.value;
      b.type = "button";
      tabs.append(b);
    }
    tabs.addEventListener("click", (e) => {
      const t = e.target.closest(".tab");
      if (!t) return;
      tabs.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
      t.classList.add("active");
      drawWall(state.gallery || []);   // 用最新列表：新生成的 run 不能因为点过 tab 就消失
    });
  }
  state.gallery = items;
  drawWall(items);
}

function drawWall(items) {
  const subject = $("#wallTabs .tab.active").dataset.subject;
  const list = items.filter((i) => !subject || i.subject === subject);
  const grid = $("#wallGrid");
  grid.textContent = "";
  resetWallLazy();
  $("#wallHint").textContent = list.length
    ? `共 ${list.length} 条 · 卡片元数据来自每个 run 的 sidecar.json / brief.json`
    : "新作品制作中：旧稿正在批量更换，更换完成的合格作品才会出现在这里。";
  for (const it of list) {
    const card = el("div", "wcard");
    if (it.video) {
      // 懒加载（SubTask 63）：进入视口附近才挂 src（preload=metadata 取首帧），
      // 之前显示纯 CSS 骨架占位；loadeddata 后骨架撤掉。无 IntersectionObserver 的浏览器直接挂 src 兜底。
      const media = el("div", "wmedia");
      media.append(el("div", "wmedia-skel"));
      const v = el("video");
      v.controls = true; v.preload = "none";
      v.dataset.src = it.video;
      v.addEventListener("loadeddata", () => media.classList.add("loaded"));
      media.append(v);
      card.append(media);
      lazyLoadMedia(v);
    }
    const body = el("div", "body");
    body.append(el("h4", "", it.topic || it.key));
    const meta = el("div", "meta-line");
    meta.append(
      tag(labelSubject(it.subject)), tag(it.grade_label || it.grade || "—"),
      tag(it.seconds ? it.seconds + "s" : "时长未知"),
      tag(it.size_mb ? it.size_mb + "MB" : "—"), tag(it.date || ""), tag(it.source));
    body.append(meta);

    const row = el("div", "wrow");
    const open = el("button", "linkbtn", "查看 / 改分镜");
    open.type = "button";
    open.addEventListener("click", () => openWall(it));
    row.append(open);
    for (const f of (it.files || []).filter((x) => ["final", "burned", "srt", "plan"].includes(x.role))) {
      const a = el("a", "linkbtn", "↓ " + f.name);
      a.href = f.url + "?download=1";
      row.append(a);
    }
    body.append(row);
    card.append(body);
    grid.append(card);
  }
}

/* 作品墙懒加载：一个全局 IntersectionObserver，重绘前 disconnect 重建 */
function resetWallLazy() {
  if (state.wallIO) { state.wallIO.disconnect(); state.wallIO = null; }
  if ("IntersectionObserver" in window) {
    state.wallIO = new IntersectionObserver((entries) => {
      for (const en of entries) {
        if (!en.isIntersecting) continue;
        const v = en.target;
        state.wallIO.unobserve(v);
        v.preload = "metadata";
        v.src = v.dataset.src;
      }
    }, { rootMargin: "200px" });
  }
}
function lazyLoadMedia(v) {
  if (state.wallIO) { state.wallIO.observe(v); return; }
  v.preload = "metadata";          // 兜底：无 IO 支持时立即挂载，行为退回改造前
  v.src = v.dataset.src;
}

async function openWall(item) {
  let plan = null;
  if (item.plan_url) {
    try {
      const r = await fetch(item.plan_url);
      const d = await r.json();
      plan = d.plan;
    } catch (e) {
      showError($("#briefError"), NET_MSG, "分镜读取失败：" + e);
      return;
    }
  }
  $("#progressCard").classList.add("hidden");
  showResult(item, plan, { result: { sidecar: item, names: {} } });
}

/* ------------------------------------------------------------------ 工具 */
const tag = (t) => el("span", "tag", t);
const labelSubject = (s) => ({ math: "数学", physics: "物理", chemistry: "化学" }[s] || s || "—");
const human = (n) => (n > 1e6 ? (n / 1e6).toFixed(1) + " MB" : Math.round(n / 1024) + " KB");

/* msg 是给人看的结论；raw（可选）是原始错误文本，进 details 折叠，保留可展开、不吞信息。 */
function showError(node, msg, raw) {
  node.textContent = "";
  node.append(el("span", "err-msg", msg));
  if (raw !== undefined && raw !== null && String(raw) && String(raw) !== msg) {
    const det = el("details", "err-raw");
    det.append(el("summary", "", "原始错误详情"));
    det.append(el("pre", "", String(raw)));
    node.append(det);
  }
  node.hidden = false;
}
function hideError(node) { node.hidden = true; node.textContent = ""; }

async function post(url, body) {
  try {
    const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" },
                                 body: JSON.stringify(body) });
    const data = await r.json().catch(() => ({}));
    return { status: r.status, data };
  } catch (e) {
    showError($("#briefError"), NET_MSG, "请求失败：" + e);
    return null;
  }
}

/* ------------------------------------------------------------------ 绑定 */
$("#fSubject").addEventListener("change", () => { savePrefs({ subject: $("#fSubject").value }); });
$("#fGrade").addEventListener("change", () => { savePrefs({ grade: $("#fGrade").value }); });
$("#fStyle").addEventListener("change", () => savePrefs({ style: $("#fStyle").value }));
$("#fQuality").addEventListener("change", () => savePrefs({ quality: $("#fQuality").value }));
$("#fSeconds").addEventListener("change", () => savePrefs({ seconds: $("#fSeconds").value }));

$("#btnClear").addEventListener("click", () => {
  $("#fRaw").value = "";
  hideError($("#briefError"));
});
$("#btnReset").addEventListener("click", () => {
  $("#fSubject").value = DEFAULTS.subject;
  $("#fGrade").value = DEFAULTS.grade;
  $("#fSeconds").value = DEFAULTS.seconds;
  $("#fStyle").value = DEFAULTS.style;
  $("#fQuality").value = DEFAULTS.quality;
  $("#fTopic").value = "";
  $("#fPrior").checked = true;
  $("#fRaw").value = "";
  try { localStorage.removeItem(PREF_KEY); } catch (e) { /* 忽略 */ }
});
$("#btnGenerate").addEventListener("click", generate);
$("#btnRegenerate").addEventListener("click", regenerate);
$("#btnImprove").addEventListener("click", improve);
$("#btnReloadPlan").addEventListener("click", () => state.plan && renderShots(state.plan));

/* ------------------------------------------------------------------ 问题反馈 */
function toggleFeedback() {
  const card = $("#feedbackCard");
  card.classList.toggle("hidden");
  hideError($("#fbError"));
  $("#fbDone").hidden = true;
  if (!card.classList.contains("hidden")) {
    card.scrollIntoView({ behavior: "smooth", block: "center" });
    $("#fFbText").focus({ preventScroll: true });
  }
}
$("#btnFeedback").addEventListener("click", toggleFeedback);
$("#btnFeedbackTop").addEventListener("click", toggleFeedback);
$("#btnFeedbackCancel").addEventListener("click", () => {
  $("#feedbackCard").classList.add("hidden");
  hideError($("#fbError"));
});
$("#btnFeedbackSubmit").addEventListener("click", async () => {
  const text = $("#fFbText").value.trim();
  if (!text) return showError($("#fbError"), "请先写反馈内容");
  const btn = $("#btnFeedbackSubmit");
  btn.disabled = true;
  let r, d;
  try {
    r = await fetch("/api/feedback", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type: $("#fFbType").value, text, contact: $("#fFbContact").value.trim() }) });
    d = await r.json().catch(() => ({}));
  } catch (e) {
    btn.disabled = false;
    return showError($("#fbError"), NET_MSG, "提交失败：" + e);
  }
  btn.disabled = false;
  if (!r.ok) return showError($("#fbError"), d.error || "提交失败，请稍后再试");
  hideError($("#fbError"));
  $("#fFbText").value = "";
  $("#fFbContact").value = "";
  $("#fbDone").hidden = false;
});

loadTopics();
loadGallery();
