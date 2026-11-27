/* ============================================================
   MusicDL · Liquid Glass — 前端逻辑
   ============================================================ */
(() => {
  'use strict';

  /* ---------- 来源汉化（精准） ---------- */
  const SOURCE_ZH = {
    // 大中华区
    'QQMusicClient': 'QQ音乐',
    'KugouMusicClient': '酷狗音乐',
    'KuwoMusicClient': '酷我音乐',
    'NeteaseMusicClient': '网易云音乐',
    'MiguMusicClient': '咪咕音乐',
    'QianqianMusicClient': '千千音乐',
    'BilibiliMusicClient': '哔哩哔哩',
    'BodianMusicClient': '波点音乐',
    'FiveSingMusicClient': '5SING',
    'StreetVoiceMusicClient': '街声',
    'SodaMusicClient': '汽水音乐',
    'MOOVMusicClient': 'MOOV',
    // 全球流媒体 / 独立
    'AppleMusicClient': 'Apple Music',
    'AudiusMusicClient': 'Audius',
    'CCMixterMusicClient': 'ccMixter',
    'DeezerMusicClient': 'Deezer',
    'FMAMusicClient': 'FMA 自由音乐',
    'JamendoMusicClient': 'Jamendo',
    'JioSaavnMusicClient': 'JioSaavn',
    'JooxMusicClient': 'JOOX',
    'OpenGameArtMusicClient': 'OpenGameArt',
    'QobuzMusicClient': 'Qobuz',
    'SoundCloudMusicClient': 'SoundCloud',
    'SpotifyMusicClient': 'Spotify',
    'SunoMusicClient': 'Suno',
    'TIDALMusicClient': 'TIDAL',
    'WikimediaCommonsMusicClient': '维基共享',
    'YouTubeMusicClient': 'YouTube',
    // 有声书 / 电台
    'ITunesMusicClient': 'iTunes 播客',
    'LizhiMusicClient': '荔枝FM',
    'LRTSMusicClient': '懒人听书',
    'QingtingMusicClient': '蜻蜓FM',
    'XimalayaMusicClient': '喜马拉雅',
    // 聚合网关
    'GDStudioMusicClient': 'GD音乐台',
    'JBSouMusicClient': '煎饼搜',
    'MP3JuiceMusicClient': 'MP3Juice',
    'MyFreeMP3MusicClient': 'MyFreeMP3',
    'TuneHubMusicClient': 'TuneHub',
    'XiaoBaiMusicClient': '小白音乐',
    // 第三方下载站
    'BuguyyMusicClient': '布谷音乐',
    'FangpiMusicClient': '放屁音乐',
    'FiveSongMusicClient': '5Song无损',
    'GequbaoMusicClient': '歌曲宝',
    'GequhaiMusicClient': '歌曲海',
    'GequkeMusicClient': '歌曲客',
    'HeishanMusicClient': '黑山音乐',
    'HTQYYMusicClient': '好听轻音乐',
    'KKWSMusicClient': '开开无损',
    'LeedodoMusicClient': '乐多多',
    'MGMP3MusicClient': '木瓜音乐',
    'MituMusicClient': '米兔音乐',
    'SgogoMusicClient': '搜歌网',
    'TwoT58MusicClient': '爱听音乐',
    'XiagebaMusicClient': '下歌吧',
    'XMFWAVMusicClient': '小蜜蜂音乐',
    'YinyuedaoMusicClient': '音悦道',
    'YinyuekuMusicClient': '音乐库',
  };
  const zh = (name) => SOURCE_ZH[name] || String(name || '').replace(/MusicClient$/, '');

  /* ---------- DOM ---------- */
  const $ = (id) => document.getElementById(id);
  const bgLayer = $('bgLayer');
  const bgPanel = $('bgPanel');
  const bgToggle = $('bgToggle');
  const bgClose = $('bgClose');
  const bgUrl = $('bgUrl');
  const bgApply = $('bgApply');
  const bgReset = $('bgReset');
  const blurRange = $('blurRange');
  const blurVal = $('blurVal');
  const brightRange = $('brightRange');
  const brightVal = $('brightVal');
  const glassRange = $('glassRange');
  const glassVal = $('glassVal');
  const keyword = $('keyword');
  const searchBtn = $('searchBtn');
  const historyPop = $('historyPop');
  const historyList = $('historyList');
  const historyClear = $('historyClear');
  const sourceTrigger = $('sourceTrigger');
  /* 面板容器就是 .source-picker（页面里没有 #sourcePicker 这个 id，
     原来取到 null，只要来源面板展开就会在点击时抛 TypeError） */
  const sourcePicker = sourceTrigger.closest('.source-picker') || sourceTrigger;
  const sourcePopover = $('sourcePopover');
  const sourceBadge = $('sourceBadge');
  const sourceList = $('sourceList');
  const sourcesFilter = $('sourcesFilter');
  const sourcesAll = $('sourcesAll');
  const sourcesNone = $('sourcesNone');
  const sourcesCount = $('sourcesCount');
  const resultsEl = $('results');
  const statusDot = $('statusDot');
  const statusText = $('statusText');
  const consoleCard = $('consoleCard');
  const consoleHead = $('consoleHead');
  const consoleBody = $('consoleBody');
  const consoleStatus = $('consoleStatus');
  const consoleBar = $('consoleBar');
  const dlConsole = $('dlConsole');
  const dlConsoleHead = $('dlConsoleHead');
  const dlConsoleBody = $('dlConsoleBody');
  const dlConsoleStatus = $('dlConsoleStatus');
  const dlConsoleSub = $('dlConsoleSub');
  const dlRingFg = $('dlRingFg');
  /* 下载面板的三块：当前任务卡 / 批次队列 / 折叠的原始日志 */
  const dlTaskCard = $('dlTaskCard');
  const dlQueue = $('dlQueue');
  const dlRawLog = $('dlRawLog');
  const dlLogToggle = $('dlLogToggle');
  /* 批量选择工具条 */
  const batchBar = $('batchBar');
  const batchAll = $('batchAll');
  const batchInvert = $('batchInvert');
  const batchCount = $('batchCount');
  const batchClear = $('batchClear');
  const batchDownload = $('batchDownload');
  /* 重复下载确认框 */
  const dupMask = $('dupMask');
  const dupList = $('dupList');
  const dupHint = $('dupHint');
  const dupClose = $('dupClose');
  const dupCancel = $('dupCancel');
  const dupConfirm = $('dupConfirm');
  const dupAllKeep = $('dupAllKeep');
  const dupAllSkip = $('dupAllSkip');
  const player = $('player');
  const playerPlay = $('playerPlay');
  const playerToggle = $('playerToggle');
  const playerTitle = $('playerTitle');
  const playerArtist = $('playerArtist');
  const playerTrack = $('playerTrack');
  const playerFill = $('playerFill');
  const playerTime = $('playerTime');
  const playerClose = $('playerClose');
  const playerVolBtn = $('playerVolBtn');
  const playerVol = $('playerVol');
  const audioEl = $('audioEl');

  const DEFAULT_BG = 'linear-gradient(165deg, #d9e6f9 0%, #edf2fb 42%, #f6e8ef 100%)';
  const SETTINGS_KEY = 'musicdl.webui.settings';
  const HISTORY_KEY = 'musicdl.webui.history';
  // 默认勾选的来源（自动过滤掉不可用的）
  const DEFAULT_SOURCES = [
    'QQMusicClient',       // QQ音乐
    'KugouMusicClient',    // 酷狗音乐
    'KuwoMusicClient',     // 酷我音乐
    'NeteaseMusicClient',  // 网易云音乐
    'MiguMusicClient',     // 咪咕音乐
    'BodianMusicClient',   // 波点音乐
  ];
  const MAX_HISTORY = 10;

  /* ---------- 状态栏 ---------- */
  function setStatus(text, kind = 'ok') {
    statusText.textContent = text;
    statusDot.className = 'dot' + (kind === 'warn' ? ' warn' : kind === 'err' ? ' err' : '');
  }

  function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, (c) => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
  }

  /* ---------- 背景设置 ---------- */
  const HINT_DEFAULT = '';   // 静态说明已去掉，这里只承载动态状态（加载中 / 失败）
  const bgClear = $('bgClear');
  const bgHint = $('bgHint');

  const settings = Object.assign(
    { url: '', blur: 0, brightness: 100, opacity: 0.4, volume: 0.7, muted: false },
    (() => { try { return JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}'); } catch { return {}; } })(),
  );
  /* 亮度范围已收紧为 0–100：老存档里可能还躺着 30–160 时代的值，读进来先夹回合法区间 */
  settings.brightness = (() => {
    const b = Number(settings.brightness);
    return Number.isFinite(b) ? Math.max(0, Math.min(100, b)) : 100;
  })();

  function setBgHint(text, kind) {
    bgHint.textContent = text;
    bgHint.className = 'hint' + (kind ? ' ' + kind : '');
  }
  function syncClearBtn() { bgClear.hidden = !bgUrl.value.trim(); }

  /* 只负责绘制，不做校验 */
  function paintBackground() {
    const url = (settings.url || '').trim();
    bgLayer.style.backgroundImage = url ? `url("${url}")` : DEFAULT_BG;
    bgUrl.value = url;
    syncClearBtn();
  }

  /* 应用背景：乐观地先画上去（避免出现空白），同时探测能否加载，失败则回退预设并提示 */
  function applyBackground() {
    const url = (settings.url || '').trim();
    if (!url) {
      paintBackground();
      setBgHint(HINT_DEFAULT, '');
      return;
    }
    bgLayer.style.backgroundImage = `url("${url}")`;
    bgUrl.value = url;
    syncClearBtn();
    setBgHint('正在加载图片…', '');

    const probe = new Image();
    probe.onload = () => setBgHint(`已加载 ${probe.naturalWidth} × ${probe.naturalHeight}`, 'ok');
    probe.onerror = () => {
      settings.url = '';
      saveSettings();
      bgLayer.style.backgroundImage = DEFAULT_BG;
      bgUrl.value = url;                 // 保留输入内容，方便改完重试
      syncClearBtn();
      setBgHint('图片加载失败：链接无效，或该站点不允许外链引用', 'err');
      setStatus('背景图片加载失败，已回退到默认背景', 'warn');
    };
    probe.src = url;
  }
  function applyFilters() {
    document.documentElement.style.setProperty('--blur', settings.blur + 'px');
    document.documentElement.style.setProperty('--brightness', settings.brightness + '%');
    blurRange.value = settings.blur;
    brightRange.value = settings.brightness;
    blurVal.textContent = settings.blur + 'px';
    brightVal.textContent = settings.brightness + '%';
    syncSliderFill(blurRange);
    syncSliderFill(brightRange);
  }
  function syncSliderFill(range) {
    const min = +range.min, max = +range.max, val = +range.value;
    range.style.setProperty('--fill', ((val - min) / (max - min)) * 100 + '%');
  }
  function applyOpacity() {
    document.documentElement.style.setProperty('--glass-alpha', settings.opacity);
    glassRange.value = Math.round(settings.opacity * 100);
    glassVal.textContent = Math.round(settings.opacity * 100) + '%';
    syncSliderFill(glassRange);
  }
  function saveSettings() { localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings)); }

  function openPanel(open) {
    bgPanel.classList.toggle('open', open);
    bgPanel.setAttribute('aria-hidden', open ? 'false' : 'true');
    if (open) moveTabIndicator();          // 打开时校正滑块位置（此时尺寸才可靠）
  }
  bgToggle.addEventListener('click', () => openPanel(!bgPanel.classList.contains('open')));
  bgClose.addEventListener('click', () => openPanel(false));
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') openPanel(false); });
  document.addEventListener('click', (e) => {
    if (!bgPanel.classList.contains('open')) return;
    if (bgPanel.contains(e.target) || bgToggle.contains(e.target)) return;
    openPanel(false);
  });

  bgApply.addEventListener('click', () => {
    const v = bgUrl.value.trim();
    if (v && !/^https?:\/\//i.test(v)) {
      setBgHint('链接需要以 http:// 或 https:// 开头', 'err');
      setStatus('请输入以 http(s):// 开头的图片链接', 'warn');
      return;
    }
    settings.url = v;
    saveSettings();
    applyBackground();
    setStatus(v ? '背景已更新' : '已恢复预设背景');
  });
  bgUrl.addEventListener('keydown', (e) => { if (e.key === 'Enter') bgApply.click(); });
  bgUrl.addEventListener('input', syncClearBtn);
  bgClear.addEventListener('click', () => {
    bgUrl.value = '';
    settings.url = '';
    syncClearBtn();
    applyBackground();
    saveSettings();
    bgUrl.focus();
    setStatus('已清除背景图片');
  });
  blurRange.addEventListener('input', () => { settings.blur = +blurRange.value; applyFilters(); saveSettings(); });
  brightRange.addEventListener('input', () => { settings.brightness = +brightRange.value; applyFilters(); saveSettings(); });
  glassRange.addEventListener('input', () => { settings.opacity = +glassRange.value / 100; applyOpacity(); saveSettings(); });
  bgReset.addEventListener('click', () => {
    settings.url = '';
    settings.blur = 0; settings.brightness = 100; settings.opacity = 0.4;
    bgUrl.value = '';
    applyBackground(); applyFilters(); applyOpacity(); saveSettings();
    setStatus('背景与滤镜已重置');
  });

  /* ---------- 设置面板：分页切换（背景 / Cookie / AI 翻译） ---------- */
  const tabBg = $('tabBg');
  const tabCookie = $('tabCookie');
  const tabAi = $('tabAi');
  const tabIndicator = $('tabIndicator');
  const pageBg = $('pageBg');
  const pageCookie = $('pageCookie');
  const pageAi = $('pageAi');
  const TABS = [
    { key: 'bg', btn: tabBg, page: pageBg },
    { key: 'cookie', btn: tabCookie, page: pageCookie },
    { key: 'ai', btn: tabAi, page: pageAi },
  ];

  /* 滑块只用 translateX 位移（位置由 CSS 百分比推算，不读 DOM 尺寸）——
     见 style.css 里的性能说明 */
  function moveTabIndicator() {
    const idx = Math.max(0, TABS.findIndex((t) => t.btn.classList.contains('active')));
    tabIndicator.classList.toggle('at-1', idx === 1);
    tabIndicator.classList.toggle('at-2', idx === 2);
  }

  let activePage = 'bg';
  let pageSwapTimer = 0;
  let panelGrowTimer = 0;
  const reducedMotion = () => {
    try { return window.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch { return false; }
  };

  /* 玻璃框高度平滑过渡：JS 钉住旧高度 → 换页 → 让 CSS transition 滑到新高度。
     动画期间 .grow 类把 overflow 设为 hidden，避免内容比框高时滚动条闪现。
     被中途打断时以「当前实测高度」作为新的起点，连续点也保持连续感。 */
  function growPanelTo(fromH) {
    const panel = bgPanel;
    clearTimeout(panelGrowTimer);
    panelGrowTimer = 0;
    const wasGrowing = panel.classList.contains('grow');
    panel.style.height = '';             // 先解除内联高度，量到新页面的自然高度
    const toH = panel.clientHeight;      // （上一次动画若没播完，此时读到的是中途高度，会算错）
    if (fromH === toH || reducedMotion() || !panel.classList.contains('open')) {
      panel.classList.remove('grow');
      panel.style.height = '';
      return;
    }
    if (!wasGrowing) panel.classList.add('grow');
    panel.style.height = fromH + 'px';
    void panel.offsetHeight;             // 让起点高度先生效，transition 才有方向
    panel.style.height = toH + 'px';
    panelGrowTimer = setTimeout(() => {
      panel.classList.remove('grow');
      panel.style.height = '';           // 交还 auto 高度，后续自适应内容/视口
      panelGrowTimer = 0;
    }, 230);
  }

  function showPanelPage(which) {
    if (which === activePage) return;
    const oldTab = TABS.find((t) => t.key === activePage);
    const newTab = TABS.find((t) => t.key === which);
    activePage = which;

    /* 标签态和滑块立刻响应：点下去就有反馈，不用等内容 */
    TABS.forEach((t) => {
      const on = t.key === which;
      t.btn.classList.toggle('active', on);
      t.btn.setAttribute('aria-selected', String(on));
    });
    moveTabIndicator();

    if (which === 'cookie') loadCookies();
    if (which === 'ai') loadAiConfig();

    /* 节奏：旧页 70ms 淡出 → 换页，玻璃框同时滑向新高度（200ms），新页淡入。
       内容只动 opacity（祖先有 34px 模糊，缩放会逐帧重采样文字）；
       框的高度用 CSS transition，动画期间 .grow 裁剪内容防滚动条闪现。 */
    clearTimeout(pageSwapTimer);
    const commit = () => {
      pageSwapTimer = 0;
      const fromH = bgPanel.clientHeight;      // 换页前的高度（旧页还在）
      TABS.forEach((t) => {
        if (t.key === which) return;
        t.page.classList.remove('page-leave', 'page-enter');
        t.page.hidden = true;
      });
      const page = newTab.page;
      page.hidden = false;
      page.classList.remove('page-enter');
      void page.offsetWidth;             // 强制一次重排，保证连续切换时动画能重播
      page.classList.add('page-enter');
      growPanelTo(fromH);
    };
    const animate = oldTab && !oldTab.page.hidden && !reducedMotion();
    if (animate) {
      oldTab.page.classList.remove('page-enter');   // 上一次的淡入还没放完就再切页时，别让它压住淡出
      oldTab.page.classList.add('page-leave');
      pageSwapTimer = setTimeout(commit, 70);
    } else {
      commit();
    }
  }
  TABS.forEach((t) => t.btn.addEventListener('click', () => showPanelPage(t.key)));

  /* ---------- Cookie 设置 ---------- */
  const quarkCookie = $('quarkCookie');
  const quarkHint = $('quarkHint');
  const quarkTags = $('quarkTags');
  const cookieSlots = $('cookieSlots');
  const cookieHint = $('cookieHint');
  const cookieSave = $('cookieSave');
  const cookieClear = $('cookieClear');

  /* 靠夸克 Cookie 的来源只列出来（它们共用上面那一个输入框） */
  function renderQuarkTags(list) {
    quarkTags.innerHTML = '';
    (list || []).forEach((s) => {
      const t = document.createElement('span');
      t.className = 'quark-tag';
      t.textContent = zh(s.name);
      t.title = s.reason || '';
      quarkTags.appendChild(t);
    });
  }

  /* 少数来源用的不是浏览器 Cookie，这里给出字段说明（保持一行到两行） */
  const COOKIE_HINTS = {
    TIDALMusicClient:
      '需会话字段：access_token / refresh_token / user_id / country_code / client_id / client_secret',
  };

  function renderCookieSlots(slots) {
    cookieSlots.innerHTML = '';
    /* 没有需要填写的来源时，整组（标题 + 空状态说明）一起收起，界面上不留空块 */
    const group = cookieSlots.closest('.pgroup');
    if (group) group.hidden = !slots.length;
    if (!slots.length) return;
    slots.forEach((s) => {
      const box = document.createElement('div');
      box.className = 'cookie-slot' + (s.value ? ' filled' : '');
      const id = 'ck_' + s.name;

      const label = document.createElement('label');
      label.setAttribute('for', id);
      label.textContent = zh(s.name);

      const input = document.createElement('input');
      input.type = 'text';
      input.id = id;
      input.dataset.src = s.name;
      input.placeholder = COOKIE_HINTS[s.name] ? '按下方格式填入' : '粘贴 Cookie';
      input.value = s.value || '';
      input.spellcheck = false;

      box.append(label, input);

      // 只有「怎么填」这种必要信息才留（格式说明），泛泛的「需要凭证」不再铺在界面上
      const tip = COOKIE_HINTS[s.name];
      if (tip) {
        const t = document.createElement('p');
        t.className = 'slot-why slot-tip';
        t.textContent = tip;
        box.appendChild(t);
      }

      cookieSlots.appendChild(box);
    });
  }

  /* 凭证页数据缓存：内容没变就不重建 DOM —— 重建会触发玻璃面板内的重排与重绘 */
  let cookiesCache = null;
  let cookiesSig = '';

  function applyCookies(d) {
    const sig = JSON.stringify([d.quark, d.quark_scope, d.quark_slots, d.slots]);
    if (sig === cookiesSig) return false;      // 内容一致，跳过（也保住用户正在输入的内容）
    cookiesSig = sig;
    quarkCookie.value = d.quark || '';
    renderQuarkTags(d.quark_slots);
    renderCookieSlots(d.slots || []);
    /* 说明性文案一律不写：缺少的夸克来源由下面那排标签自证，其他平台看有没有输入框即可 */
    quarkHint.textContent = '';
    cookieHint.textContent = '';
    return true;
  }

  async function loadCookies(force) {
    if (cookiesCache && !force) { applyCookies(cookiesCache); return; }
    if (!cookiesCache) cookieHint.textContent = '正在读取…';
    try {
      const resp = await fetch('/api/cookies');
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      cookiesCache = await resp.json();
      applyCookies(cookiesCache);
    } catch (err) {
      cookieHint.textContent = '读取失败：' + err.message;
    }
  }

  async function saveCookies(payload, okMsg) {
    cookieSave.disabled = true;
    const old = cookieSave.textContent;
    cookieSave.textContent = '保存并重新检测中…';
    try {
      const resp = await fetch('/api/cookies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const d = await resp.json();
      if (!resp.ok) throw new Error(d.error || 'HTTP ' + resp.status);
      cookiesCache = d;
      cookiesSig = '';                   // 强制按新数据重建
      applyCookies(d);
      setStatus(`${okMsg}：可用来源 ${d.available} 个，仍有 ${d.unavailable} 个需凭证`, 'ok');
      await loadSources(true);          // 刷新可用性，但保留用户已勾选的来源
    } catch (err) {
      setStatus('凭证保存失败：' + err.message, 'err');
      cookieHint.textContent = '保存失败：' + err.message;
    } finally {
      cookieSave.disabled = false;
      cookieSave.textContent = old;
    }
  }

  function collectCookieSlots() {
    const sources = {};
    cookieSlots.querySelectorAll('input[data-src]').forEach((i) => {
      const v = i.value.trim();
      if (v) sources[i.dataset.src] = v;
    });
    return sources;
  }

  cookieSave.addEventListener('click', () => {
    saveCookies({ quark: quarkCookie.value.trim(), sources: collectCookieSlots() }, '凭证已保存');
  });

  cookieClear.addEventListener('click', () => {
    if (!confirm('确定清空全部已保存的 Cookie？')) return;
    quarkCookie.value = '';
    cookieSlots.querySelectorAll('input[data-src]').forEach((i) => { i.value = ''; });
    saveCookies({ quark: '', sources: {} }, '凭证已清空');
  });

  /* ---------- AI 翻译设置 ---------- */
  const aiEnabled = $('aiEnabled');
  const aiBaseUrl = $('aiBaseUrl');
  const aiKey = $('aiKey');
  const aiModel = $('aiModel');
  const aiTarget = $('aiTarget');
  const aiBilingual = $('aiBilingual');
  const aiHint = $('aiHint');
  const aiStatus = $('aiStatus');
  const aiSave = $('aiSave');
  const aiTest = $('aiTest');
  let aiLoaded = false;

  function fillAiConfig(d) {
    const c = d.config || {};
    aiEnabled.checked = !!c.enabled;
    aiBaseUrl.value = c.base_url || '';
    aiModel.value = c.model || '';
    aiKey.value = '';
    aiKey.placeholder = c.api_key_set ? `已保存：${c.api_key}（留空则不修改）` : 'sk-…';
    aiBilingual.checked = c.embed_bilingual !== false;

    const langs = d.target_langs || [];
    if (!aiTarget.options.length) {
      langs.forEach((l) => {
        const o = document.createElement('option');
        o.value = l;
        o.textContent = l;
        aiTarget.appendChild(o);
      });
    }
    aiTarget.value = c.target_lang || (langs[0] || '中文');
    aiStatus.textContent = '';
    aiLoaded = true;
  }

  async function loadAiConfig() {
    if (aiLoaded) return;            // 已加载过就不重复请求
    try {
      const resp = await fetch('/api/ai');
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      fillAiConfig(await resp.json());
    } catch (err) {
      aiHint.textContent = '读取失败：' + err.message;
    }
  }

  function collectAiConfig() {
    const body = {
      enabled: aiEnabled.checked,
      base_url: aiBaseUrl.value.trim(),
      model: aiModel.value.trim(),
      target_lang: aiTarget.value,
      translate_lyrics: true,
      embed_bilingual: aiBilingual.checked,
    };
    const k = aiKey.value.trim();
    if (k) body.api_key = k;         // 留空表示沿用已保存的密钥
    return body;
  }

  aiSave.addEventListener('click', async () => {
    aiSave.disabled = true;
    const old = aiSave.textContent;
    aiSave.textContent = '保存中…';
    try {
      const resp = await fetch('/api/ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(collectAiConfig()),
      });
      const d = await resp.json();
      if (!resp.ok) throw new Error(d.error || 'HTTP ' + resp.status);
      aiLoaded = false;
      fillAiConfig(d);
      setStatus(aiEnabled.checked ? `AI 翻译已启用，目标语言：${aiTarget.value}` : 'AI 翻译已保存（未启用）', 'ok');
    } catch (err) {
      setStatus('AI 配置保存失败：' + err.message, 'err');
      aiHint.textContent = '保存失败：' + err.message;
    } finally {
      aiSave.disabled = false;
      aiSave.textContent = old;
    }
  });

  aiTest.addEventListener('click', async () => {
    aiTest.disabled = true;
    const old = aiTest.textContent;
    aiTest.textContent = '测试中…';
    aiStatus.textContent = '正在请求模型…';
    try {
      const resp = await fetch('/api/ai/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(collectAiConfig()),
      });
      const d = await resp.json();
      if (d.ok) {
        aiStatus.textContent = `连接正常，模型返回：${d.message}`;
        setStatus('AI 连接测试通过', 'ok');
      } else {
        aiStatus.textContent = '连接失败：' + d.message;
        setStatus('AI 连接测试失败', 'err');
      }
    } catch (err) {
      aiStatus.textContent = '测试失败：' + err.message;
    } finally {
      aiTest.disabled = false;
      aiTest.textContent = old;
    }
  });

  aiEnabled.addEventListener('change', () => {
    aiStatus.textContent = '';       // 说明文案已去掉；状态只在测试连接/出错时显示
  });

  /* ---------- 来源选择器 ---------- */
  const ALL_SOURCES = [];
  const UNAVAILABLE = {};   // {name: reason}
  const selectedSources = new Set();
  let filterText = '';
  let sourceOpen = false;

  function allNames() { return [...ALL_SOURCES, ...Object.keys(UNAVAILABLE)]; }
  function filteredSources() {
    const all = allNames();
    if (!filterText) return all;
    const q = filterText.toLowerCase();
    return all.filter((n) => n.toLowerCase().includes(q) || zh(n).toLowerCase().includes(q));
  }
  function updateBadges() {
    sourceBadge.textContent = selectedSources.size;
    sourcesCount.textContent = `${selectedSources.size} / ${allNames().length}`;
  }
  function toggleSource(open) {
    sourceOpen = open;
    sourcePopover.classList.toggle('open', open);
    sourceTrigger.classList.toggle('open', open);
    sourceTrigger.setAttribute('aria-expanded', String(open));
    if (open) {
      if (historyOpen) toggleHistory(false);   // 与「最近搜索」互斥，避免两块重叠
      sourcesFilter.focus();
    }
  }
  sourceTrigger.addEventListener('click', () => toggleSource(!sourceOpen));
  document.addEventListener('click', (e) => {
    if (!sourceOpen || sourcePicker.contains(e.target)) return;
    toggleSource(false);
  });

  function renderSources() {
    const items = filteredSources();
    sourceList.innerHTML = '';
    if (!allNames().length) { sourceList.innerHTML = '<div class="source-empty">无可用来源</div>'; return; }
    if (!items.length) { sourceList.innerHTML = '<div class="source-empty">没有匹配的来源</div>'; return; }

    const frag = document.createDocumentFragment();
    items.forEach((name) => {
      const disabled = name in UNAVAILABLE;
      const row = document.createElement('label');
      row.className = 'source-item' + (selectedSources.has(name) ? ' active' : '') + (disabled ? ' disabled' : '');
      row.innerHTML = '<input type="checkbox" /><span class="source-name"></span>' + (disabled ? '<span class="source-hint">需凭证</span>' : '');
      const cb = row.querySelector('input');
      cb.checked = selectedSources.has(name);
      cb.disabled = disabled;
      row.querySelector('.source-name').textContent = zh(name);
      row.title = disabled ? `${name} · ${UNAVAILABLE[name]}` : name;
      cb.addEventListener('change', () => {
        if (cb.checked) selectedSources.add(name); else selectedSources.delete(name);
        row.classList.toggle('active', cb.checked);
        updateBadges();
      });
      frag.appendChild(row);
    });
    sourceList.appendChild(frag);
  }

  sourcesFilter.addEventListener('input', () => { filterText = sourcesFilter.value.trim(); renderSources(); });
  sourcesAll.addEventListener('click', () => { filteredSources().forEach((n) => selectedSources.add(n)); renderSources(); updateBadges(); });
  sourcesNone.addEventListener('click', () => { filteredSources().forEach((n) => selectedSources.delete(n)); renderSources(); updateBadges(); });

  /* keepSelection=true 时不重置默认勾选（保存凭证后刷新可用性用） */
  async function loadSources(keepSelection = false) {
    try {
      const resp = await fetch('/api/sources');
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      const data = await resp.json();
      ALL_SOURCES.length = 0;
      ALL_SOURCES.push(...(data.sources || []));
      for (const k in UNAVAILABLE) delete UNAVAILABLE[k];
      Object.assign(UNAVAILABLE, data.unavailable || {});
      if (!keepSelection) {
        DEFAULT_SOURCES.filter((s) => ALL_SOURCES.includes(s)).forEach((s) => selectedSources.add(s));
      } else {
        // 已选来源若变为不可用则移除；新变为可用的不自动勾选
        for (const s of [...selectedSources]) {
          if (!ALL_SOURCES.includes(s)) selectedSources.delete(s);
        }
      }
      renderSources();
      updateBadges();
    } catch (err) {
      sourceList.innerHTML = '<div class="source-empty">来源加载失败（后端未连接？）</div>';
      setStatus('后端未连接：来源列表不可用', 'warn');
    }
  }

  /* ---------- 搜索历史 ---------- */
  function loadHistory() { try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); } catch { return []; } }
  function saveHistory(h) { localStorage.setItem(HISTORY_KEY, JSON.stringify(h)); }
  function addHistory(kw) {
    kw = kw.trim();
    if (!kw) return;
    saveHistory([kw, ...loadHistory().filter((x) => x !== kw)].slice(0, MAX_HISTORY));
  }
  function removeHistory(kw) { saveHistory(loadHistory().filter((x) => x !== kw)); }

  const CLOCK_SVG = '<svg class="clock" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15.5 14"/></svg>';

  function renderHistory() {
    const hist = loadHistory();
    historyList.innerHTML = '';
    if (!hist.length) { historyList.innerHTML = '<div class="history-empty">暂无搜索记录</div>'; return; }
    const frag = document.createDocumentFragment();
    hist.forEach((kw) => {
      const li = document.createElement('li');
      li.className = 'history-item';
      li.innerHTML = CLOCK_SVG + '<span class="kw"></span><span class="del">✕</span>';
      li.querySelector('.kw').textContent = kw;
      li.addEventListener('mousedown', (e) => {
        e.preventDefault();
        keyword.value = kw;
        toggleHistory(false);
        doSearch();
      });
      li.querySelector('.del').addEventListener('mousedown', (e) => {
        e.stopPropagation();
        e.preventDefault();
        removeHistory(kw);
        renderHistory();
      });
      frag.appendChild(li);
    });
    historyList.appendChild(frag);
  }

  let historyOpen = false;
  function toggleHistory(open) {
    historyOpen = open;
    historyPop.classList.toggle('open', open);
    if (open && sourceOpen) toggleSource(false);   // 与「来源」互斥，避免两块重叠
  }
  keyword.addEventListener('focus', () => { renderHistory(); toggleHistory(true); });
  keyword.addEventListener('blur', () => setTimeout(() => toggleHistory(false), 130));
  historyClear.addEventListener('mousedown', (e) => {
    e.preventDefault();
    saveHistory([]);
    renderHistory();
  });

  /* ---------- 搜索 ---------- */
  /* ---------- 搜索过程控制台（可收缩） ---------- */
  function setConsoleCollapsed(v) { consoleCard.classList.toggle('collapsed', v); }
  consoleHead.addEventListener('click', () => setConsoleCollapsed(!consoleCard.classList.contains('collapsed')));
  consoleHead.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      setConsoleCollapsed(!consoleCard.classList.contains('collapsed'));
    }
  });

  function clockStr() {
    const d = new Date(), p = (n) => String(n).padStart(2, '0');
    return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
  }

  function logLine(text, cls) {
    const row = document.createElement('div');
    row.className = 'log-line' + (cls ? ' ' + cls : '');
    const t = document.createElement('span');
    t.className = 't';
    t.textContent = clockStr();
    const s = document.createElement('span');
    s.textContent = text;
    row.append(t, s);
    consoleBody.appendChild(row);
    consoleBody.scrollTop = consoleBody.scrollHeight;
  }

  let progTotal = 0, progDone = 0;

  function setProgress(done, total) {
    progDone = done;
    progTotal = total;
    const pct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;
    consoleBar.style.width = pct + '%';
    const track = consoleBar.parentElement;
    if (track) {
      track.setAttribute('aria-valuemin', '0');
      track.setAttribute('aria-valuemax', String(Math.max(total, 1)));
      track.setAttribute('aria-valuenow', String(done));
    }
    if (total > 0) consoleStatus.textContent = `${done} / ${total} 个来源`;
  }

  function consoleReset() {
    consoleBody.innerHTML = '';
    consoleBar.style.width = '0%';
    consoleStatus.textContent = '准备中…';
    progTotal = 0;
    progDone = 0;
    consoleCard.hidden = false;
    consoleCard.classList.add('running');   // 让进度条流光动起来
    setConsoleCollapsed(true);      // 默认收缩，需要时点表头展开
  }

  /* ---------- 批量选择：复选框状态 ---------- */
  /* 结果是每次搜索重绘的数组，选中状态单独存 id 集合，重绘不丢选择 */
  let currentResults = [];          // 最近一次搜索结果（已排序）
  const resultMap = new Map();      // id -> 结果对象
  const selectedIds = new Set();

  function updateBatchBar() {
    const total = currentResults.length;
    const n = selectedIds.size;
    batchBar.hidden = total === 0;
    batchCount.textContent = n ? `已选 ${n} / ${total} 项` : `已选 0 项（共 ${total} 项）`;
    batchDownload.disabled = n === 0;          // 未选中任何项时入口保持置灰
    batchAll.checked = total > 0 && n === total;
    batchAll.indeterminate = n > 0 && n < total;
    batchClear.disabled = n === 0;
    batchInvert.disabled = total === 0;
    /* 卡片上的勾选态与集合保持一致（重绘/全选/反选都走这里刷新） */
    resultsEl.querySelectorAll('.result').forEach((card) => {
      const box = card.querySelector('.pick');
      if (!box) return;
      const on = selectedIds.has(box.dataset.id);
      box.checked = on;
      card.classList.toggle('picked', on);
    });
  }

  function togglePick(id, on) {
    if (!id) return;
    if (on) selectedIds.add(id); else selectedIds.delete(id);
    updateBatchBar();
  }

  batchAll.addEventListener('change', () => {
    if (batchAll.checked) currentResults.forEach((r) => selectedIds.add(r.id));
    else selectedIds.clear();
    updateBatchBar();
  });
  batchInvert.addEventListener('click', () => {
    currentResults.forEach((r) => {
      if (selectedIds.has(r.id)) selectedIds.delete(r.id);
      else selectedIds.add(r.id);
    });
    updateBatchBar();
  });
  batchClear.addEventListener('click', () => {
    selectedIds.clear();
    updateBatchBar();
  });
  batchDownload.addEventListener('click', () => {
    const picked = currentResults.filter((r) => selectedIds.has(r.id));
    if (!picked.length) {
      setStatus('还没有选中任何歌曲', 'warn');
      return;
    }
    downloadWithDuplicateCheck(picked);
  });

  /* ---------- 重复检测：下载前比对曲库 ---------- */
  /* 服务端按「文件名 / 标签标题命中」判重，艺术家与专辑作为补充冲突点列出来。
     有重复时弹确认框：每条可单独选继续/跳过，也能一次性全选。 */
  const dupState = { rows: [], resolve: null };

  function openDupModal(rows) {
    /* 注意：这里不要动 dupState.resolve —— 调用方是「先拿 resolve 再开框」，
       在这里清掉它会让 await 永远不返回（点开始下载后整条链路静默挂起）。 */
    dupState.rows = rows;
    dupList.innerHTML = rows.map((r, i) => `
      <div class="dup-row" data-i="${i}" data-mode="skip">
        <div class="dup-row-main">
          <div class="dup-row-title">${escapeHtml(r.song.song_name || r.song.name || '(未知)')}
            <span class="dup-row-artist">${escapeHtml(r.song.singers || r.song.artist || '')}</span>
          </div>
          <div class="dup-row-hit">
            已有：<code>${escapeHtml(r.hits[0].filename)}</code>
            <span class="dup-tags">${(r.hits[0].conflicts || []).map((c) => `<span class="dup-tag">${escapeHtml(c)}</span>`).join('')}</span>
          </div>
          ${r.hits[0].artist || r.hits[0].album ? `<div class="dup-row-meta">库内：${escapeHtml([r.hits[0].artist, r.hits[0].album].filter(Boolean).join(' · '))}${r.hitCount > 1 ? ` · 另有 ${r.hitCount - 1} 个文件命中` : ''}</div>` : ''}
        </div>
        <label class="dup-switch">
          <input type="checkbox" class="dup-keep" />
          <span>继续下载</span>
        </label>
      </div>`).join('');

    const total = rows.length;
    dupHint.textContent = `共 ${total} 首与曲库重复，默认全部跳过；需要覆盖的逐条勾选「继续下载」。`;
    dupList.querySelectorAll('.dup-row').forEach((row) => {
      const box = row.querySelector('.dup-keep');
      const sync = () => {
        row.dataset.mode = box.checked ? 'keep' : 'skip';
        row.classList.toggle('keep', box.checked);
      };
      box.addEventListener('change', sync);
      /* 点整行也能切换，手机上不用瞄准小方框 */
      row.addEventListener('click', (e) => {
        if (e.target === box || e.target.closest('.dup-switch')) return;
        box.checked = !box.checked;
        sync();
      });
    });
    dupMask.hidden = false;
    dupMask.classList.add('show');
    const first = dupList.querySelector('.dup-keep');
    if (first) first.focus();
  }

  function closeDupModal(choice) {
    dupMask.classList.remove('show');
    dupMask.hidden = true;
    const rows = dupState.rows.map((r, i) => {
      const row = dupList.querySelector(`.dup-row[data-i="${i}"]`);
      const keep = !!(row && row.dataset.mode === 'keep');
      return { song: r.song, keep };
    });
    if (typeof dupState.resolve === 'function') dupState.resolve(choice === 'cancel' ? null : rows);
    dupState.resolve = null;
    dupState.rows = [];
  }

  dupClose.addEventListener('click', () => closeDupModal('cancel'));
  dupCancel.addEventListener('click', () => closeDupModal('cancel'));
  dupAllKeep.addEventListener('click', () => {
    dupList.querySelectorAll('.dup-row').forEach((row) => {
      row.querySelector('.dup-keep').checked = true;
      row.dataset.mode = 'keep';
      row.classList.add('keep');
    });
  });
  dupAllSkip.addEventListener('click', () => {
    dupList.querySelectorAll('.dup-row').forEach((row) => {
      row.querySelector('.dup-keep').checked = false;
      row.dataset.mode = 'skip';
      row.classList.remove('keep');
    });
  });
  dupConfirm.addEventListener('click', () => closeDupModal('ok'));
  dupMask.addEventListener('click', (e) => { if (e.target === dupMask) closeDupModal('cancel'); });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !dupMask.hidden) closeDupModal('cancel');
  });

  /* 问服务端这若干条里哪些重复；返回 {dups: [...], error}，fail-open（查不到就照常下载） */
  async function checkDuplicates(songs) {
    const ids = songs.map((s) => s.id).filter(Boolean);
    if (!ids.length) return { dups: [] };
    try {
      const resp = await fetch('/api/check-duplicates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids }),
      });
      if (!resp.ok) return { dups: [], error: 'HTTP ' + resp.status };
      const data = await resp.json();
      const byId = new Map((data.items || []).map((x) => [x.id, x]));
      const dups = [];
      songs.forEach((s) => {
        const r = byId.get(s.id);
        if (r && r.duplicate && r.hits && r.hits.length) {
          dups.push({ song: s, hits: r.hits, hitCount: r.hit_count || r.hits.length });
        }
      });
      return { dups, libraryCount: data.library_count || 0 };
    } catch (err) {
      return { dups: [], error: String((err && err.message) || err) };
    }
  }

  /* 把查重 + 确认框合成一步：返回需要继续下载的歌曲列表（被跳过的返回 skipped 数量） */
  async function resolveDuplicates(songs) {
    const { dups, error, libraryCount } = await checkDuplicates(songs);
    if (error) {
      dlLog(`重复检测不可用（${error}），按原计划下载`, 'dim');
      return { proceed: songs, skipped: 0 };
    }
    if (!dups.length) {
      if (libraryCount) dlLog(`重复检测：${songs.length} 首与曲库 ${libraryCount} 个文件比对，无重复`, 'dim');
      return { proceed: songs, skipped: 0 };
    }
    dlLog(`重复检测：${dups.length} 首命中曲库`, 'head');
    const choice = await new Promise((resolve) => {
      /* 先开框（openDupModal 不碰 resolve），再挂 resolve，顺序反过来会被清空 */
      openDupModal(dups);
      dupState.resolve = resolve;
    });
    if (!choice) return { proceed: null, skipped: 0 };      // 用户取消整次下载
    const keep = new Set(choice.filter((c) => c.keep).map((c) => c.song.id));
    const proceed = songs.filter((s) => !dups.some((d) => d.song.id === s.id) || keep.has(s.id));
    const skipped = songs.length - proceed.length;
    dups.forEach((d) => {
      if (!keep.has(d.song.id)) dlLog(`跳过重复：${d.song.song_name || ''}（${(d.hits[0].conflicts || []).join('/')}）`, 'dim');
    });
    return { proceed, skipped };
  }

  /* ---------- 下载详情（坞内，点击展开 / 收起，同播放栏思路） ---------- */  /* 面板分三层：当前任务卡（曲名/艺术家/来源/状态/进度/失败原因）→ 批次队列 → 可折叠原始日志 */
  const DL_STATUS = {
    queued: { text: '排队中', cls: 'queued' },
    running: { text: '下载中', cls: 'running' },
    done: { text: '已完成', cls: 'done' },
    fail: { text: '失败', cls: 'fail' },
    skipped: { text: '已跳过重复', cls: 'skipped' },
  };
  let dlTasks = [];                 // 本批次任务：[{id,title,artist,source,status,pct,stage,error,fname}]
  let dlCurrentId = null;

  function setDlOpen(open) {
    dlConsole.classList.toggle('open', open);
    dlConsoleHead.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  dlConsoleHead.addEventListener('click', () => setDlOpen(!dlConsole.classList.contains('open')));
  dlLogToggle.addEventListener('click', () => {
    const open = dlRawLog.hidden;
    dlRawLog.hidden = !open;
    dlLogToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    dlLogToggle.classList.toggle('on', open);
    if (open) dlRawLog.scrollTop = dlRawLog.scrollHeight;
  });
  function setDlConsoleRing(pct) {
    const p = Math.max(0, Math.min(100, Number(pct) || 0));
    dlRingFg.style.strokeDashoffset = String(100 - p);   // 周长按 100 设计
  }

  /* 原始日志：逐行 append，自动滚到底。默认展开（不点「日志」也看得到过程） */
  function dlLog(text, cls) {
    const row = document.createElement('div');
    row.className = 'log-line' + (cls ? ' ' + cls : '');
    const t = document.createElement('span');
    t.className = 't';
    t.textContent = clockStr();
    const s = document.createElement('span');
    s.textContent = text;
    row.append(t, s);
    dlRawLog.appendChild(row);
    if (!dlRawLog.hidden) dlRawLog.scrollTop = dlRawLog.scrollHeight;
  }

  function dlResetBatch() {
    dlTasks = [];
    dlCurrentId = null;
    dlQueue.innerHTML = '';
    dlTaskCard.hidden = true;
    dlTaskCard.innerHTML = '';
    dlRawLog.innerHTML = '';
    /* 新一批开始时日志保持展开：默认就能看到过程，需要时才点「日志」收起 */
    dlRawLog.hidden = false;
    dlLogToggle.classList.add('on');
    dlLogToggle.setAttribute('aria-expanded', 'true');
    dlConsoleBody.scrollTop = 0;
    dlConsole.classList.add('show');     // 有下载时才出现在坞里
    setDlOpen(true);                     // 默认展开，方便直接看到过程
    setDlConsoleRing(0);
    dlRefreshStatus();
  }

  function dlTask(id) {
    return dlTasks.find((t) => t.id === id) || null;
  }

  /* 队列行：每条任务一行，含状态徽标与细进度条；当前任务高亮 */
  function dlRenderQueue() {
    dlQueue.innerHTML = '';
    dlTasks.forEach((t, i) => {
      const row = document.createElement('div');
      row.className = 'dlq-row' + (t.id === dlCurrentId ? ' active' : '');
      row.dataset.status = t.status;
      const badge = DL_STATUS[t.status] || DL_STATUS.queued;
      row.innerHTML = `
        <span class="dlq-idx">${i + 1}</span>
        <span class="dlq-main">
          <span class="dlq-title" title="${escapeHtml(t.title)}">${escapeHtml(t.title)}</span>
          <span class="dlq-meta">${escapeHtml(t.artist || '未知艺术家')} · ${escapeHtml(zh(t.source))}</span>
          <span class="dlq-bar"><span class="dlq-fill" style="width:${Math.max(0, Math.min(100, t.pct || 0))}%"></span></span>
        </span>
        <span class="dlq-badge ${badge.cls}">${badge.text}</span>`;
      if (t.status === 'fail' && t.error) row.title = t.error;
      dlQueue.appendChild(row);
    });
  }

  /* 当前任务卡：一眼能读到的信息层级（曲名最大、状态与进度其次、失败原因独占一行） */
  function dlRenderTask() {
    const t = dlTask(dlCurrentId);
    if (!t) { dlTaskCard.hidden = true; dlTaskCard.innerHTML = ''; return; }
    const badge = DL_STATUS[t.status] || DL_STATUS.queued;
    dlTaskCard.hidden = false;
    dlTaskCard.dataset.status = t.status;
    dlTaskCard.innerHTML = `
      <div class="dlt-top">
        <div class="dlt-titles">
          <div class="dlt-title" title="${escapeHtml(t.title)}">${escapeHtml(t.title)}</div>
          <div class="dlt-sub">${escapeHtml(t.artist || '未知艺术家')}<span class="dlt-dot">·</span>${escapeHtml(zh(t.source))}</div>
        </div>
        <span class="dlt-badge ${badge.cls}">${badge.text}</span>
      </div>
      <div class="dlt-progress">
        <div class="dlt-bar"><div class="dlt-fill" id="dlTaskFill"></div></div>
        <span class="dlt-pct" id="dlTaskPct">0%</span>
      </div>
      <div class="dlt-stage" id="dlTaskStage">${escapeHtml(t.stage || '等待开始')}</div>
      ${t.status === 'fail' && t.error ? `<div class="dlt-error"><b>失败原因</b>${escapeHtml(t.error)}</div>` : ''}`;
    dlSetPct(t.pct || 0);
  }

  function dlSetPct(pct) {
    const t = dlTask(dlCurrentId);
    if (!t) return;
    t.pct = Math.max(0, Math.min(100, Number(pct) || 0));
    const fill = $('dlTaskFill');
    const label = $('dlTaskPct');
    if (fill) fill.style.width = t.pct + '%';
    if (label) label.textContent = t.pct + '%';
    setDlConsoleRing(t.pct);
    const row = dlQueue.querySelector('.dlq-row.active .dlq-fill');
    if (row) row.style.width = t.pct + '%';
  }

  function dlSetStage(pct, stage) {
    const t = dlTask(dlCurrentId);
    if (!t) return;
    if (typeof pct === 'number') dlSetPct(pct);
    if (stage) {
      t.stage = stage;
      const el = $('dlTaskStage');
      if (el) el.textContent = stage;
    }
  }

  function dlSetStatus(id, status, patch) {
    const t = dlTask(id);
    if (!t) return;
    t.status = status;
    Object.assign(t, patch || {});
    if (id === dlCurrentId) dlRenderTask();
    dlRenderQueue();
    dlRefreshStatus();
  }

  /* 头部总状态：N 个完成 / N 个失败 / 第 i/N 个下载中 */
  function dlRefreshStatus() {
    const total = dlTasks.length;
    const done = dlTasks.filter((t) => t.status === 'done').length;
    const fail = dlTasks.filter((t) => t.status === 'fail').length;
    const skip = dlTasks.filter((t) => t.status === 'skipped').length;
    const running = dlTasks.find((t) => t.status === 'running');
    if (!total) {
      dlConsoleStatus.textContent = '就绪';
      dlConsoleSub.textContent = '等待下载任务';
      return;
    }
    const idx = running ? dlTasks.indexOf(running) + 1 : 0;
    const head = running ? `下载中 ${idx}/${total}` : `已结束 ${done + fail + skip}/${total}`;
    dlConsoleStatus.textContent = head;
    const bits = [`完成 ${done}`];
    if (fail) bits.push(`失败 ${fail}`);
    if (skip) bits.push(`跳过 ${skip}`);
    dlConsoleSub.textContent = bits.join(' · ');
    if (!running) setDlConsoleRing(total ? 100 * (done + fail + skip) / total : 0);
  }

  /* ---------- 搜索（流式，实时显示运行过程） ---------- */
  let searching = false;      // 搜索期间别让 30 秒一次的健康检查把状态栏冲掉

  async function doSearch() {
    const kw = keyword.value.trim();
    if (!kw) { setStatus('请输入关键词', 'warn'); return; }
    if (!selectedSources.size) { setStatus('请至少选择一个来源', 'warn'); return; }

    addHistory(kw);
    toggleHistory(false);          // 搜索开始即收起历史，避免遮住结果区
    searching = true;
    searchBtn.disabled = true;
    searchBtn.textContent = '搜索中…';
    resultsEl.innerHTML = '';
    /* 新搜索：旧结果的选中集一并作废，工具条收起 */
    currentResults = [];
    resultMap.clear();
    selectedIds.clear();
    updateBatchBar();
    consoleReset();
    setStatus('正在搜索 "' + kw + '" …');

    let final = null;
    const onEvent = (e) => {
      switch (e.type) {
        case 'phase':        logLine(e.text, 'head'); break;
        case 'log':          logLine(e.text, 'dim'); break;
        case 'start':
          logLine(`→ ${zh(e.source)} 开始搜索`);
          setProgress(progDone, progTotal + 1);
          break;
        case 'done_source':
          logLine(`✓ ${zh(e.source)} 完成：${e.count} 条 (${e.elapsed}s)`, 'ok');
          setProgress(progDone + 1, progTotal);
          break;
        case 'error_source':
          logLine(`✗ ${zh(e.source)} 失败：${e.error} (${e.elapsed}s)`, 'err');
          setProgress(progDone + 1, progTotal);
          break;
        case 'fatal':        throw new Error(e.error);
        case 'finished':
          final = e;
          setProgress(progTotal, progTotal);          // 收满进度条
          logLine(`全部完成：${e.total} 条结果 · ${e.ok_sources} 个来源成功 · 用时 ${e.elapsed}s`, 'head');
          break;
      }
    };

    try {
      const resp = await fetch('/api/search/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keyword: kw, sources: [...selectedSources] }),
      });
      if (!resp.ok || !resp.body) throw new Error('HTTP ' + resp.status);

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let idx;
        while ((idx = buf.indexOf('\n')) >= 0) {
          const raw = buf.slice(0, idx);
          buf = buf.slice(idx + 1);
          if (!raw.trim()) continue;
          let evt = null;
          try { evt = JSON.parse(raw); } catch { continue; }
          if (evt) onEvent(evt);
        }
      }

      if (final) {
        renderResults(final.results || [], kw);
        const failedN = Object.keys(final.failed_sources || {}).length;
        consoleStatus.textContent = `完成 · ${final.total} 条` + (failedN ? ` · ${failedN} 个来源失败` : '');
        setStatus(`搜索完成：${final.total} 条结果`);
      } else {
        consoleStatus.textContent = '已结束（未收到结果）';
        setStatus('搜索结束但未收到结果', 'warn');
      }
    } catch (err) {
      logLine('异常：' + err.message, 'err');
      consoleStatus.textContent = '出错';
      resultsEl.innerHTML = `<div class="glass card empty"><div class="big">⚠️</div>${escapeHtml(err.message)}</div>`;
      setStatus('搜索失败：' + err.message, 'err');
    } finally {
      consoleCard.classList.remove('running');   // 结束即停流光
      searching = false;
      searchBtn.disabled = false;
      searchBtn.textContent = '搜索';
    }
  }

  searchBtn.addEventListener('click', doSearch);
  keyword.addEventListener('keydown', (e) => { if (e.key === 'Enter') doSearch(); });

  /* ---------- 在线试听（音频经后端代理，绕开防盗链与跨域） ---------- */
  let currentSong = null;
  let currentBtn = null;

  function fmtTime(s) {
    if (!isFinite(s) || s < 0) s = 0;
    return `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
  }

  function resetPreviewBtn() {
    if (currentBtn) {
      currentBtn.classList.remove('active');
      currentBtn.textContent = '试听';
      currentBtn = null;
    }
  }

  let seeking = false, seekPreview = 0;

  /* 坞里的圆 = 「展开 / 收起」开关：点击切换。
     悬停只把圆点换成 ">"，展开后显示 "<"，再次点击收回。 */
  function setPlayerOpen(open) {
    player.classList.toggle('open', open);
    playerToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  playerToggle.addEventListener('click', () => {
    setPlayerOpen(!player.classList.contains('open'));
  });

  /* ---------- 展开的面板：点面板外面自动收起 ----------
     坞里的播放栏 / 下载栏是点击展开、会一直挡在内容上的浮层，之前只能再点同一个圆才能收。
     这里统一处理「点别处收起」：
       · 用 pointerdown 而不是 click —— 面板内拖滑杆/进度条时指针乱跑也不会误收；
       · 只认「目标不在面板所在的坞内」的按下，所以点面板里的按钮、拖音量都不会关；
       · 播放器与下载栏互相独立，点哪一个的圆，另一个会顺手收起（同一时间只留一个浮层）。 */
  document.addEventListener('pointerdown', (e) => {
    const t = e.target;
    if (!(t instanceof Node)) return;
    if (player.classList.contains('open') && !player.contains(t)) setPlayerOpen(false);
    if (dlConsole.classList.contains('open') && !dlConsole.contains(t)) setDlOpen(false);
  });

  /* Esc 也可收起这几个浮层（设置面板原有逻辑在文件上方） */
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    setPlayerOpen(false);
    setDlOpen(false);
    toggleSource(false);
  });

  function closePlayer() {
    try { audioEl.pause(); } catch (e) { /* noop */ }
    audioEl.removeAttribute('src');
    try { audioEl.load(); } catch (e) { /* noop */ }
    player.classList.remove('show', 'playing', 'open', 'seeking');
    playerToggle.setAttribute('aria-expanded', 'false');
    playerFill.style.width = '0%';
    playerTime.textContent = '0:00 / 0:00';
    resetPreviewBtn();
    currentSong = null;
  }

  async function preview(song, btn) {
    if (currentSong && currentSong.id === song.id) {          // 同一个：切换播放/暂停
      if (audioEl.paused) {
        try { await audioEl.play(); } catch (e) { setStatus('试听失败：' + e.message, 'err'); }
      } else {
        audioEl.pause();
      }
      return;
    }
    resetPreviewBtn();
    currentBtn = btn;
    if (btn) { btn.classList.add('active'); btn.textContent = '加载中…'; }
    currentSong = song;
    playerTitle.textContent = song.song_name || '(未知)';
    playerArtist.textContent = String(song.singers || '').trim();
    playerFill.style.width = '0%';
    playerTime.textContent = '0:00 / 0:00';
    player.classList.add('show');
    audioEl.src = '/api/stream?id=' + encodeURIComponent(song.id);
    try {
      await audioEl.play();
      setStatus('正在试听：' + (song.song_name || ''));
    } catch (e) {
      setStatus('试听失败（可能受版权或防盗链限制）', 'warn');
    }
  }

  playerPlay.addEventListener('click', () => {
    if (!audioEl.getAttribute('src')) return;
    if (audioEl.paused) audioEl.play().catch(() => {}); else audioEl.pause();
  });
  playerClose.addEventListener('click', closePlayer);

  audioEl.addEventListener('play', () => {
    player.classList.add('playing');
    if (currentBtn) currentBtn.textContent = '暂停';
  });
  audioEl.addEventListener('pause', () => {
    player.classList.remove('playing');
    if (currentBtn) currentBtn.textContent = '试听';
  });
  audioEl.addEventListener('ended', () => {
    player.classList.remove('playing');
    playerFill.style.width = '0%';
    if (currentBtn) currentBtn.textContent = '试听';
  });
  audioEl.addEventListener('error', () => {
    if (!audioEl.getAttribute('src')) return;
    setStatus('该结果无法在线试听（可能受版权或防盗链限制）', 'warn');
    player.classList.remove('playing');
    if (currentBtn) currentBtn.textContent = '试听';
  });
  audioEl.addEventListener('loadedmetadata', () => {
    playerTime.textContent = `0:00 / ${fmtTime(audioEl.duration)}`;
  });
  audioEl.addEventListener('timeupdate', () => {
    const d = audioEl.duration, t = audioEl.currentTime;
    const pct = (isFinite(d) && d > 0) ? Math.min(100, (t / d) * 100) : 0;
    if (!seeking) {
      playerFill.style.width = pct + '%';
      playerTime.textContent = `${fmtTime(t)} / ${fmtTime(d)}`;
    }
  });

  /* ---------- 音量（记忆上次设置；静音与「音量拖到 0」统一视为无声） ---------- */
  const VOL_DEFAULT = 0.7;
  let lastNonZeroVolume = VOL_DEFAULT;    // 拖到 0 之后再点喇叭，回到这个音量

  function clampVolume(v) {
    const n = Number(v);
    return isFinite(n) ? Math.min(1, Math.max(0, n)) : VOL_DEFAULT;
  }

  /* 唯一的写入口：settings → <audio> 与 UI 一起更新，避免两边状态打架 */
  function applyVolume() {
    settings.volume = clampVolume(settings.volume);
    settings.muted = settings.muted === true;
    if (settings.volume > 0) lastNonZeroVolume = settings.volume;
    const silent = settings.muted || settings.volume === 0;
    const pct = Math.round(settings.volume * 100);

    audioEl.volume = settings.volume;
    audioEl.muted = settings.muted;

    /* 静音时滑杆停在 0，恢复时回到记忆的音量 */
    playerVol.value = String(silent ? 0 : pct);
    syncSliderFill(playerVol);
    playerVol.setAttribute('aria-valuetext', silent ? '静音' : pct + '%');

    playerVolBtn.classList.toggle('muted', silent);
    playerVolBtn.classList.toggle('low', !silent && settings.volume <= 0.45);
    playerVolBtn.setAttribute('aria-pressed', silent ? 'true' : 'false');
    playerVolBtn.setAttribute('aria-label', silent ? '取消静音' : '静音');
    playerVolBtn.title = silent ? '已静音，点击恢复音量' : `音量 ${pct}%（点击静音）`;
  }

  playerVolBtn.addEventListener('click', () => {
    if (settings.muted || settings.volume === 0) {          // 当前无声 → 恢复
      settings.muted = false;
      settings.volume = lastNonZeroVolume;
    } else {
      settings.muted = true;
    }
    applyVolume();
    saveSettings();
    setStatus(settings.muted ? '已静音' : `音量 ${Math.round(settings.volume * 100)}%`);
  });

  /* 拖动（含键盘方向键）即时生效；拖到 0 自动算静音，拖回来自动取消静音 */
  playerVol.addEventListener('input', () => {
    const v = clampVolume(+playerVol.value / 100);
    settings.volume = v;
    if (v > 0) settings.muted = false;
    applyVolume();
    saveSettings();
  });
  playerVol.addEventListener('change', () => {
    setStatus(settings.volume > 0 ? `音量 ${Math.round(settings.volume * 100)}%` : '已静音');
  });

  /* 进度条：可按住前后拖动（pointer 事件，含捕获，拖出边界也不断） */
  function applySeek(clientX) {
    const d = audioEl.duration;
    if (!isFinite(d) || d <= 0) return false;
    const rect = playerTrack.getBoundingClientRect();
    if (rect.width <= 0) return false;
    const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
    seekPreview = ratio * d;
    playerFill.style.width = (ratio * 100) + '%';
    playerTime.textContent = `${fmtTime(seekPreview)} / ${fmtTime(d)}`;
    return true;
  }

  playerTrack.addEventListener('pointerdown', (e) => {
    if (!applySeek(e.clientX)) return;
    seeking = true;
    player.classList.add('seeking');       // 拖动中锁定展开，拖出边界也不收起
    try { playerTrack.setPointerCapture(e.pointerId); } catch (err) { /* noop */ }
    e.preventDefault();
  });
  playerTrack.addEventListener('pointermove', (e) => {
    if (seeking) applySeek(e.clientX);
  });
  function endSeek(e) {
    if (!seeking) return;
    seeking = false;
    player.classList.remove('seeking');
    const d = audioEl.duration;
    if (isFinite(d) && d > 0) audioEl.currentTime = seekPreview;
    try { playerTrack.releasePointerCapture(e.pointerId); } catch (err) { /* noop */ }
  }
  playerTrack.addEventListener('pointerup', endSeek);
  playerTrack.addEventListener('pointercancel', () => {
    seeking = false;
    player.classList.remove('seeking');
  });

  /* ---------- 结果渲染（紧凑） ---------- */
  const MUSIC_SVG = '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>';
  const LOSSLESS_EXTS = new Set(['FLAC', 'WAV', 'ALAC', 'APE', 'WV', 'TTA', 'DSF', 'DFF']);

  /* 把后端返回的 "113.33 MB" 这类字符串换算成字节数，用于排序 */
  function sizeToBytes(s) {
    const m = String(s || '').match(/([\d.]+)\s*(TB|GB|MB|KB|B)?/i);
    if (!m) return -1;
    const n = parseFloat(m[1]);
    if (!isFinite(n)) return -1;
    const mul = { B: 1, KB: 1024, MB: 1024 ** 2, GB: 1024 ** 3, TB: 1024 ** 4 };
    return n * (mul[(m[2] || 'B').toUpperCase()] || 1);
  }

  function renderResults(results, kw) {
    if (!results.length) {
      currentResults = [];
      resultMap.clear();
      selectedIds.clear();
      updateBatchBar();
      resultsEl.innerHTML = `<div class="glass card empty"><div class="big">🔍</div>没有找到 "${escapeHtml(kw)}" 相关结果</div>`;
      return;
    }
    /* 按文件大小从大到小排序（拿不到大小的排到最后） */
    const ordered = [...results].sort((a, b) => sizeToBytes(b.file_size) - sizeToBytes(a.file_size));
    currentResults = ordered;
    resultMap.clear();
    ordered.forEach((r) => resultMap.set(r.id, r));
    /* 结果换了：保留仍在本次结果里的选择，其余丢弃 */
    [...selectedIds].forEach((id) => { if (!resultMap.has(id)) selectedIds.delete(id); });
    resultsEl.innerHTML = '';
    ordered.forEach((r, i) => {
      const card = document.createElement('div');
      card.className = 'glass card result';
      card.dataset.id = r.id;
      card.style.animationDelay = Math.min(i, 14) * 28 + 'ms';    // 逐条浮现
      const artist = String(r.singers || r.artist || '').trim();
      const ext = String(r.ext || '').replace(/^\./, '').toUpperCase();
      const size = String(r.file_size || '').trim();
      const album = String(r.album || '').trim();
      const duration = String(r.duration || '').trim();
      const lossless = LOSSLESS_EXTS.has(ext);
      card.innerHTML = `
        <label class="pick-wrap" title="选择这首歌">
          <input type="checkbox" class="pick" data-id="${escapeHtml(r.id)}"
                 aria-label="选择 ${escapeHtml(r.song_name || r.name || '(未知)')}"${selectedIds.has(r.id) ? ' checked' : ''} />
        </label>
        <div class="result-art"></div>
        <div class="result-main">
          <div class="result-title">${escapeHtml(r.song_name || r.name || '(未知)')}${artist ? `<span class="result-artist">${escapeHtml(artist)}</span>` : ''}</div>
          <div class="result-meta">
            <span class="meta-source">${escapeHtml(zh(r.source))}</span>
            ${album ? `<span class="meta-album" title="${escapeHtml(album)}">${escapeHtml(album)}</span>` : ''}
            ${duration ? `<span class="meta-duration">${escapeHtml(duration)}</span>` : ''}
            ${ext ? `<span class="meta-ext${lossless ? ' lossless' : ''}">${escapeHtml(ext)}</span>` : ''}
            ${size ? `<span class="meta-size">${escapeHtml(size)}</span>` : ''}
          </div>
        </div>
        <div class="result-actions">
          ${r.previewable ? '<button class="glass-btn pv">试听</button>' : ''}
          <button class="glass-btn dl">
            <span class="btn-text">下载</span>
            <svg class="dl-ring" viewBox="0 0 36 36" aria-hidden="true">
              <circle class="dl-ring-bg" cx="18" cy="18" r="15.9155"></circle>
              <circle class="dl-ring-fg" cx="18" cy="18" r="15.9155"></circle>
            </svg>
          </button>
        </div>`;

      /* 封面图标：经 /api/cover 代理（绕开各平台防盗链），失败则回退成音符图标 */
      const artEl = card.querySelector('.result-art');
      if (r.cover_url) {
        const img = document.createElement('img');
        img.className = 'result-art-img';
        img.alt = '';
        img.loading = 'lazy';
        img.decoding = 'async';
        img.addEventListener('load', () => img.classList.add('loaded'));
        img.addEventListener('error', () => {
          img.remove();
          artEl.classList.add('fallback');
          artEl.innerHTML = MUSIC_SVG;
        });
        img.src = '/api/cover?id=' + encodeURIComponent(r.id);
        artEl.appendChild(img);
      } else {
        artEl.classList.add('fallback');
        artEl.innerHTML = MUSIC_SVG;
      }

      const pv = card.querySelector('.pv');
      if (pv) pv.addEventListener('click', () => preview(r, pv));
      const pick = card.querySelector('.pick');
      if (pick) {
        pick.addEventListener('change', () => togglePick(pick.dataset.id, pick.checked));
        /* 点复选框本体或标题区域都能选中；点「试听/下载」时不改变选择 */
        pick.addEventListener('click', (e) => e.stopPropagation());
      }
      card.addEventListener('click', (e) => {
        if (e.target.closest('button, .pick-wrap')) return;
        const box = card.querySelector('.pick');
        if (!box) return;
        box.checked = !box.checked;
        togglePick(box.dataset.id, box.checked);
      });
      card.querySelector('.dl').addEventListener('click', (e) => downloadWithDuplicateCheck([r], e.currentTarget));
      if (selectedIds.has(r.id)) card.classList.add('picked');
      resultsEl.appendChild(card);
    });
    updateBatchBar();
  }

  /* ---------- 下载（流式，圆环进度） ---------- */
  function setDlRing(btn, pct) {
    const fg = btn && btn.querySelector('.dl-ring-fg');
    if (!fg) return;
    const p = Math.max(0, Math.min(100, Number(pct) || 0));
    fg.style.strokeDashoffset = String(100 - p);     // 周长按 100 设计
  }

  /* 单条下载：流事件映射到任务卡与队列行，返回 {ok, saved, error}（异常不向外抛，批量才能继续） */
  async function downloadOne(song, btn, opts = {}) {
    const id = song.id;
    const title = song.song_name || song.name || '(未知)';
    const artist = String(song.singers || song.artist || '').trim();

    if (!opts.keepPanel) dlResetBatch();       // 单条下载自己清面板；批量由 downloadBatch 统一清
    if (!dlTask(id)) {
      dlTasks.push({ id, title, artist, source: song.source || '',
                     status: 'running', pct: 0, stage: '准备中', error: '', fname: '' });
      dlRenderQueue();
    }
    dlCurrentId = id;
    dlSetStatus(id, 'running', { stage: '准备中' });
    dlLog(`▼ ${title}${artist ? ' — ' + artist : ''}`, 'head');

    if (btn) {
      btn.classList.add('downloading');
      btn.disabled = true;
      setDlRing(btn, 0);
    }
    const label = btn ? btn.querySelector('.btn-text') : null;
    if (label) label.textContent = '下载中';
    setStatus('正在下载：' + title);

    let done = null;
    const onEvent = (e) => {
      switch (e.type) {
        case 'phase':
          dlLog(e.text, 'dim');
          dlSetStage(null, e.text);
          break;
        case 'log':
          dlLog(e.text, 'dim');
          break;
        case 'progress':
          if (btn) setDlRing(btn, e.pct);
          dlSetStage(e.pct, e.text);
          break;
        case 'fatal':
          throw new Error(e.error || '下载失败');
        case 'finished':
          done = e;
          break;
        default:
          break;
      }
    };

    try {
      const resp = await fetch('/api/download/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: song.id, song }),
      });
      if (!resp.ok || !resp.body) throw new Error('HTTP ' + resp.status);

      const reader = resp.body.getReader();
      const dec = new TextDecoder();
      let buf = '';
      for (;;) {
        const { done: rdone, value } = await reader.read();
        if (rdone) break;
        buf += dec.decode(value, { stream: true });
        let i;
        while ((i = buf.indexOf('\n')) >= 0) {
          const raw = buf.slice(0, i);
          buf = buf.slice(i + 1);
          if (!raw.trim()) continue;
          let evt = null;
          try { evt = JSON.parse(raw); } catch { continue; }
          if (evt) onEvent(evt);
        }
      }

      if (btn) setDlRing(btn, 100);
      const saved = done && done.saved && done.saved[0];
      const fname = saved && saved.save_path ? String(saved.save_path).split(/[\\/]/).pop() : '';
      dlSetPct(100);
      dlSetStage(100, saved && saved.lyrics_embedded ? '完成（歌词已内置）' : '完成');
      dlSetStatus(id, 'done', { pct: 100, fname, stage: '完成' });
      dlLog(fname ? `✓ 完成：${fname}` : '✓ 完成', 'ok');
      setStatus(fname ? `下载完成：${fname}` : '下载完成', 'ok');
      if (btn) {
        setTimeout(() => {                            // 让圆环停留一下再复原
          btn.classList.remove('downloading');
          btn.disabled = false;
          setDlRing(btn, 0);
          if (label) label.textContent = '下载';
        }, 1500);
      }
      return { ok: true, saved, error: '' };
    } catch (err) {
      const msg = String((err && err.message) || err);
      dlSetStatus(id, 'fail', { error: msg });
      dlLog('✗ ' + msg, 'err');
      setStatus('下载失败：' + msg, 'err');
      if (btn) {
        btn.classList.remove('downloading');
        btn.disabled = false;
        setDlRing(btn, 0);
        if (label) label.textContent = '下载';
      }
      return { ok: false, saved: null, error: msg };
    }
  }

  /* 单条下载：先查重（有重复弹确认框），再走流式下载；返回 {ok, saved, error, skipped} */
  async function downloadWithDuplicateCheck(songs, btn) {
    try {
      /* 面板只重置一次，且必须在查重之前：
         否则查重写进日志的「重复检测 N 首 / 跳过重复 xxx」会被重置冲掉。 */
      dlResetBatch();
      const { proceed, skipped } = await resolveDuplicates(songs);
      if (!proceed) return { ok: false, cancelled: true, saved: null, error: '', skipped: 0 };
      if (!proceed.length) {
        setStatus('已跳过全部重复项', 'warn');
        return { ok: false, saved: null, error: '', skipped };
      }
      if (songs.length === 1) {
        /* keepPanel：面板刚重置过，别再清一次（会连同查重日志一起清掉） */
        const res = await downloadOne(proceed[0], btn || null, { keepPanel: true });
        return { ...res, skipped };
      }
      const stats = await downloadBatch(proceed, { keepPanel: true });
      return { ok: true, saved: null, error: '', skipped, stats };
    } catch (err) {
      /* 任何意外都别静默：写进状态栏与下载面板，避免「点了没反应」 */
      const msg = String((err && err.message) || err);
      setStatus('下载启动失败：' + msg, 'err');
      dlLog('✗ 下载启动失败：' + msg, 'err');
      return { ok: false, saved: null, error: msg, skipped: 0 };
    }
  }

  /* 批量下载：串行执行，避免并发抢带宽与面板错乱；每条各自更新队列行 */
  async function downloadBatch(list, opts = {}) {
    const songs = (list || []).filter((s) => s && s.id);
    if (!songs.length) return;
    if (!opts.keepPanel) dlResetBatch();
    songs.forEach((s) => {
      dlTasks.push({
        id: s.id,
        title: s.song_name || s.name || '(未知)',
        artist: String(s.singers || s.artist || '').trim(),
        source: s.source || '',
        status: 'queued', pct: 0, stage: '排队中', error: '', fname: '',
      });
    });
    dlRenderQueue();
    dlRefreshStatus();
    setStatus(`批量下载：共 ${songs.length} 首`);

    let ok = 0;
    let bad = 0;
    for (let i = 0; i < songs.length; i++) {
      const s = songs[i];
      dlConsoleStatus.textContent = `批量下载 ${i + 1}/${songs.length}`;
      const card = [...resultsEl.querySelectorAll('.result')].find((c) => c.dataset.id === s.id);
      const btn = card ? card.querySelector('.dl') : null;
      const res = await downloadOne(s, btn, { keepPanel: true });
      if (res && res.ok) ok += 1; else bad += 1;
      updateBatchBar();
    }
    dlRefreshStatus();
    dlConsoleSub.textContent = `完成 ${ok} · 失败 ${bad} · 共 ${songs.length}`;
    setStatus(`批量下载结束：成功 ${ok} / ${songs.length}`, bad ? 'warn' : 'ok');
    return { ok, bad, total: songs.length };
  }

  /* ---------- 初始化 ---------- */
  applyBackground();
  applyFilters();
  applyOpacity();
  applyVolume();          // 音量必须在任何一次 play() 之前落到 <audio> 上
  loadSources();
  moveTabIndicator();
  loadCookies();          // 预取凭证页数据：首次切到 Cookie 分页时无需等待

  /* 支持 #bg / #cookie / #ai 深链直接定位到某个设置分页（方便分享与排查） */
  const DEEP = { '#bg': 'bg', '#cookie': 'cookie', '#ai': 'ai' };
  if (DEEP[location.hash]) {
    openPanel(true);
    showPanelPage(DEEP[location.hash]);
  }

  setInterval(async () => {
    if (searching) return;        // 搜索中不抢状态栏：不然「正在搜索…」会被这句顶掉
    try {
      const r = await fetch('/api/health');
      if (r.ok) {
        const d = await r.json();
        setStatus(d.ready ? '后端就绪 · 已加载 ' + (d.sources || 0) + ' 个来源' : '后端未完全就绪（依赖缺失）', d.ready ? 'ok' : 'warn');
      }
    } catch { setStatus('后端未连接', 'err'); }
  }, 30000);
})();
