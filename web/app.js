const app = document.getElementById("app");
const toastRoot = document.getElementById("toast-root");

const LANGUAGE_OPTIONS = [
  ["en", "English (US)"],
  ["tr", "Turkish"],
  ["de", "German"],
  ["fr", "French"],
  ["es", "Spanish"],
  ["ja", "Japanese"],
  ["auto", "Auto-detect"],
];

const MODEL_OPTIONS = [
  ["distil-large-v3 (fast)", "Distil Large v3 · Fast"],
  ["large-v3 (accurate)", "Whisper Large v3 · Accurate"],
];

const PHASES = ["validating", "fetching", "downloading", "transcribing", "exporting", "completed"];

const state = {
  bootstrap: null,
  form: {
    mode: "single_url",
    source_value: "",
    platform_hint: "youtube",
    language: "en",
    model: "distil-large-v3 (fast)",
    speaker_detection: false,
  },
  onboardingDraft: {
    intent: "",
    source_preference: "",
  },
  lastCreatedSecret: null,
  keyComposerOpen: false,
  historyFilter: "all",
  historyQuery: "",
  historyPage: 1,
  historyPerPage: 10,
  pollHandle: null,
};

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatDateTime(value) {
  if (!value) return "Just now";
  try {
    return new Date(value).toLocaleString([], {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return value;
  }
}

function relativeTime(value) {
  if (!value) return "Just now";
  const delta = Date.now() - new Date(value).getTime();
  const minutes = Math.round(delta / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.round(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

function formatMinutes(value = 0) {
  return `${Number(value).toFixed(value >= 100 ? 0 : 1)} min`;
}

function statusBadge(job) {
  const resolvedStatus = normalizedJobStatus(job);
  const tone =
    resolvedStatus === "completed"
      ? "bg-primary-fixed text-on-primary-fixed-variant"
      : resolvedStatus === "failed"
        ? "bg-error-container text-on-error-container"
        : "bg-secondary-container text-on-secondary-container";
  return `<span class="inline-flex rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-[0.18em] ${tone}">${escapeHtml(resolvedStatus)}</span>`;
}

function sourceIcon(job) {
  const platform = (job.platform || "").toLowerCase();
  if (platform.includes("youtube")) return "smart_display";
  if (platform.includes("instagram") || platform.includes("reels")) return "movie";
  if (platform.includes("tiktok")) return "music_video";
  if (platform.includes("upload")) return "upload_file";
  return "api";
}

function normalizedJobStatus(job) {
  if (job.status === "completed" || job.status === "failed") return job.status;
  return "processing";
}

function jobOriginLabel(job) {
  return job.via === "api" ? "API Integration" : "Web Dashboard";
}

function jobOriginIcon(job) {
  return job.via === "api" ? "api" : "language";
}

async function apiGet(path) {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

async function apiPost(path, body, isFormData = false) {
  const response = await fetch(path, {
    method: "POST",
    headers: isFormData ? undefined : { "Content-Type": "application/json", Accept: "application/json" },
    body: isFormData ? body : JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}

async function apiDelete(path) {
  const response = await fetch(path, { method: "DELETE", headers: { Accept: "application/json" } });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Delete failed");
  return data;
}

function toast(message) {
  const el = document.createElement("div");
  el.className = "toast";
  el.innerHTML = `<div class="text-sm font-medium leading-relaxed">${escapeHtml(message)}</div>`;
  toastRoot.appendChild(el);
  window.setTimeout(() => {
    el.remove();
  }, 2800);
}

function navigate(path) {
  if (window.location.pathname === path) return;
  history.pushState({}, "", path);
  render();
}

function bootstrapFormDefaults() {
  if (!state.bootstrap) return;
  state.form.language = state.bootstrap.settings.default_language || "en";
  state.form.model = state.bootstrap.settings.default_model || "distil-large-v3 (fast)";
  state.form.speaker_detection = !!state.bootstrap.settings.speaker_detection;
  state.onboardingDraft.intent = state.bootstrap.onboarding.intent || "";
  state.onboardingDraft.source_preference = state.bootstrap.onboarding.source_preference || "";
}

async function refreshBootstrap() {
  state.bootstrap = await apiGet("/api/bootstrap");
  bootstrapFormDefaults();
}

function appSidebar(active) {
  const link = (path, icon, label, key) => {
    const activeCls =
      active === key
        ? "bg-white text-primary font-bold shadow-sm"
        : "text-on-surface/60 hover:bg-white/50";
    return `
      <button data-nav="${path}" class="flex w-full items-center gap-3 rounded-md px-4 py-2 text-left text-[0.875rem] transition-all duration-300 ${activeCls}">
        <span class="material-symbols-outlined">${icon}</span>
        <span>${label}</span>
      </button>
    `;
  };

  return `
    <aside class="hidden lg:flex fixed left-0 top-0 z-40 h-full w-64 flex-col bg-[#f5f3ee] py-6">
      <div class="px-8 mb-10">
        <button data-nav="/" class="text-left">
          <h1 class="text-lg font-headline italic text-on-surface">StoryToText</h1>
          <p class="mt-1 text-[0.65rem] uppercase tracking-widest text-on-surface/40">Premium Transcription</p>
        </button>
      </div>
      <nav class="flex-1 px-4 space-y-1">
        ${link("/dashboard", "dashboard", "Dashboard", "dashboard")}
        ${link("/new", "add_circle", "New Transcription", "new")}
        ${link("/history", "history", "History", "history")}
        ${link("/api-keys", "key", "API Keys", "keys")}
        ${link("/billing", "payments", "Billing", "billing")}
        ${link("/settings", "settings", "Settings", "settings")}
      </nav>
      <div class="mt-auto px-6">
        <p class="mb-3 text-[10px] font-bold uppercase tracking-[0.22em] text-on-surface/30">Current Plan</p>
        <button data-action="plan-toast" class="w-full rounded-md bg-gradient-to-br from-primary to-primary-container py-3 text-sm font-bold text-on-primary shadow-editorial transition-opacity hover:opacity-90">
          Upgrade Plan
        </button>
        <div class="mt-6 space-y-2 border-t border-outline-variant/10 pt-4">
          <button data-nav="/docs" class="flex w-full items-center gap-3 px-2 py-1 text-left text-xs text-on-surface/60 transition-colors hover:text-primary">
            <span class="material-symbols-outlined text-base ${active === "docs" ? "text-primary" : ""}">menu_book</span>
            Documentation
          </button>
          <button data-action="support-toast" class="flex w-full items-center gap-3 px-2 py-1 text-left text-xs text-on-surface/60 transition-colors hover:text-primary">
            <span class="material-symbols-outlined text-base">help_outline</span>
            Support
          </button>
        </div>
      </div>
    </aside>
  `;
}

function appTopbar(title, overline = "") {
  const user = state.bootstrap?.user || {};
  return `
    <header class="fixed top-0 z-30 h-20 w-full bg-surface/92 backdrop-blur-md lg:ml-64 lg:w-[calc(100%-16rem)]">
      <div class="flex h-20 items-center justify-between px-6 lg:px-10">
        <div class="flex items-center gap-4">
          <span class="material-symbols-outlined text-on-surface/40">menu</span>
          <div>
            ${overline ? `<p class="text-[0.65rem] uppercase tracking-[0.22em] text-primary/55">${escapeHtml(overline)}</p>` : ""}
            <h2 class="font-headline text-2xl text-primary">${escapeHtml(title)}</h2>
          </div>
        </div>
        <div class="flex items-center gap-6">
          <button data-action="notifications-toast" class="material-symbols-outlined text-on-surface/40 transition-opacity hover:opacity-70">notifications</button>
          <button data-nav="/settings" class="group flex items-center gap-3 text-left">
            <div class="hidden text-right sm:block">
              <p class="text-[0.65rem] font-bold uppercase tracking-[0.2em] text-on-surface">${escapeHtml((user.full_name || "Archive Access").toUpperCase())}</p>
              <p class="text-[11px] text-on-surface/40">${escapeHtml(state.bootstrap?.billing.plan || "Professional Plan")}</p>
            </div>
            <span class="material-symbols-outlined text-3xl text-on-surface/35 transition-colors group-hover:text-primary">account_circle</span>
          </button>
        </div>
      </div>
    </header>
  `;
}

function marketingNav(active = "") {
  const item = (path, label, key) => `
    <button data-nav="${path}" class="border-b-2 pb-1 font-headline text-sm font-medium tracking-tight transition-colors ${
      active === key ? "border-primary text-primary" : "border-transparent text-on-surface/65 hover:text-primary"
    }">${label}</button>
  `;

  return `
    <header class="fixed top-0 z-50 w-full bg-surface/80 shadow-[0_20px_40px_rgba(27,28,25,0.05)] backdrop-blur-md">
      <div class="mx-auto flex h-16 max-w-7xl items-center justify-between px-8">
        <button data-nav="/" class="font-headline text-xl font-bold text-on-surface">StoryToText</button>
        <nav class="hidden items-center gap-8 md:flex">
          ${item("/", "Product", "product")}
          ${item("/pricing", "Pricing", "pricing")}
          ${item("/docs", "Developers", "developers")}
          ${item("/resources", "Resources", "resources")}
        </nav>
        <div class="flex items-center gap-4">
          <button data-nav="/dashboard" class="hidden text-sm font-medium text-on-surface/70 transition-colors hover:text-primary sm:block">Log In</button>
          <button data-action="start-flow" class="rounded-md bg-primary px-5 py-2 text-sm font-semibold text-on-primary transition-opacity hover:opacity-90">
            Get Started
          </button>
        </div>
      </div>
    </header>
  `;
}

function appShell(active, title, content, overline = "") {
  return `
    <div class="story-shell app-surface">
      ${appSidebar(active)}
      ${appTopbar(title, overline)}
      <main class="page-fade px-6 pb-10 pt-24 lg:ml-64 lg:px-10 lg:pb-12">${content}</main>
    </div>
  `;
}

function marketingShell(content, active = "") {
  return `
    <div class="story-shell">
      ${marketingNav(active)}
      <main class="page-fade pt-32">${content}</main>
    </div>
  `;
}

function renderLanding(section = "") {
  const startLabel = state.bootstrap?.onboarding?.completed ? "Open Dashboard" : "Start free";
  const content = `
    <section class="mx-auto max-w-7xl px-8 mb-24">
      <div class="grid items-center gap-16 lg:grid-cols-2">
        <div>
          <span class="inline-block rounded-sm bg-primary-fixed px-3 py-1 text-[10px] font-bold uppercase tracking-[0.22em] text-on-primary-fixed-variant">Premium Transcription Engine</span>
          <h1 class="mt-8 max-w-2xl font-headline text-[clamp(3.4rem,7vw,5.8rem)] font-bold leading-[0.92] tracking-tight">
            Turn viral videos into <span class="italic text-primary">prompt-ready</span> text.
          </h1>
          <p class="mt-8 max-w-xl text-xl leading-relaxed text-secondary">
            The archival-grade tool for creators and content operators. Extract knowledge from YouTube, Reels, and TikTok with perfect semantic structure for your AI workflows.
          </p>
          <div class="mt-10 flex flex-wrap gap-4">
            <button data-action="start-flow" class="rounded-md bg-primary px-8 py-4 text-lg font-semibold text-on-primary shadow-editorial transition-opacity hover:opacity-90">${startLabel}</button>
            <button data-nav="/docs" class="flex items-center gap-3 rounded-md bg-surface-container-high px-8 py-4 text-lg font-semibold text-on-surface transition-colors hover:bg-surface-container-highest">
              <span class="material-symbols-outlined" style="font-variation-settings:'FILL' 1">play_circle</span>
              Watch demo
            </button>
          </div>
        </div>
        <div class="relative">
          <div class="hero-orb rounded-xl p-8 shadow-editorial">
            <div class="space-y-6">
              <div class="rounded-md bg-white/88 p-5 ghost-ring">
                <div class="mb-3 flex items-center gap-3">
                  <div class="h-2 w-2 rounded-full bg-primary"></div>
                  <span class="text-[10px] font-bold uppercase tracking-[0.22em] text-secondary">Step 01: Connect Source</span>
                </div>
                <div class="flex gap-2">
                  <div class="flex-1 rounded-sm bg-surface-container-low px-4 py-2 text-sm text-secondary">https://youtube.com/watch?v=...</div>
                  <div class="rounded-sm bg-primary px-4 py-2 text-sm font-bold text-on-primary">Paste</div>
                </div>
              </div>
              <div class="rounded-md bg-white/80 p-5 ghost-ring opacity-70">
                <div class="mb-3 flex items-center gap-3">
                  <div class="h-2 w-2 rounded-full bg-secondary"></div>
                  <span class="text-[10px] font-bold uppercase tracking-[0.22em] text-secondary">Step 02: Semantic Analysis</span>
                </div>
                <div class="h-2 overflow-hidden rounded-full bg-surface-container-low">
                  <div class="h-full w-2/3 bg-primary-container"></div>
                </div>
              </div>
              <div class="rounded-md bg-white/88 p-5 ghost-ring">
                <div class="mb-4 flex items-center gap-3">
                  <div class="h-2 w-2 rounded-full bg-green-600"></div>
                  <span class="text-[10px] font-bold uppercase tracking-[0.22em] text-secondary">Step 03: Structured Export</span>
                </div>
                <div class="space-y-3">
                  <div class="h-3 rounded-sm bg-surface-container-low"></div>
                  <div class="h-3 w-5/6 rounded-sm bg-surface-container-low"></div>
                  <div class="h-3 w-4/6 rounded-sm bg-primary-fixed"></div>
                </div>
              </div>
            </div>
          </div>
          <div class="absolute -right-10 -top-10 -z-10 h-64 w-64 rounded-full bg-primary-fixed/25 blur-3xl"></div>
        </div>
      </div>
    </section>

    <section class="mb-24 overflow-hidden bg-surface-container-low py-12">
      <div class="mx-auto max-w-7xl px-8">
        <div class="flex flex-col items-center justify-between gap-8 opacity-60 grayscale transition-all duration-700 hover:grayscale-0 md:flex-row">
          <span class="text-[10px] font-bold uppercase tracking-[0.3em] text-secondary">Supported Networks</span>
          <div class="flex items-center gap-12 font-headline text-2xl font-bold italic md:gap-24">
            <span>YouTube</span>
            <span>Instagram</span>
            <span>TikTok</span>
            <span>Vimeo</span>
          </div>
        </div>
      </div>
    </section>

    <section class="mx-auto mb-32 max-w-7xl px-8 text-center">
      <h2 class="mx-auto max-w-3xl font-headline text-3xl italic leading-tight text-on-surface-variant md:text-4xl">
        "Built for AI-assisted creators and content operators who treat information as a high-value asset."
      </h2>
    </section>

    <section class="mx-auto mb-32 max-w-7xl px-8">
      <div class="grid gap-12 md:grid-cols-3">
        ${[
          ["01", "The Ingest", "Simply drop a link or upload a file. Our engine fetches high-fidelity audio streams bypassing platform compression where possible."],
          ["02", "Deep Extraction", "Proprietary diarization identifies speakers, timestamps every sentence, and cleans 'filler' words for a polished script output."],
          ["03", "Structured Export", "Receive your content in Markdown, JSON, or TXT—pre-formatted with metadata tags ready for your favorite LLM or CMS."],
        ]
          .map(
            ([index, title, body]) => `
              <div class="space-y-6">
                <span class="font-headline text-5xl italic text-primary/30 transition-colors hover:text-primary">${index}</span>
                <h3 class="font-headline text-3xl font-bold">${title}</h3>
                <p class="leading-relaxed text-secondary">${body}</p>
              </div>
            `,
          )
          .join("")}
      </div>
    </section>

    <section id="resources" class="mb-32 bg-surface-container-low py-28">
      <div class="mx-auto max-w-7xl px-8">
        <div class="mb-16">
          <span class="mb-2 block text-xs font-bold uppercase tracking-[0.22em] text-primary">Capabilities</span>
          <h2 class="font-headline text-5xl font-bold">The Archivist's Toolkit</h2>
        </div>
        <div class="grid gap-6 md:grid-cols-12">
          <div class="min-h-[320px] rounded-xl bg-white p-10 md:col-span-8">
            <div>
              <span class="material-symbols-outlined mb-6 text-primary">link</span>
              <h3 class="font-headline text-3xl font-bold">Single-Link Magic</h3>
              <p class="mt-4 max-w-md text-secondary">Instantly convert any viral reel or thread into a structured transcript. No login required for your first 3 extracts.</p>
            </div>
            <div class="mt-10 rounded-lg bg-surface-container-low p-8">
              <div class="mx-auto flex max-w-xl items-center gap-3 rounded-md bg-on-surface px-4 py-3 text-surface">
                <span class="material-symbols-outlined">play_circle</span>
                <span class="flex-1 text-sm text-white/75">Paste URL. Receive transcript.</span>
                <span class="material-symbols-outlined text-primary-fixed">arrow_forward</span>
              </div>
            </div>
          </div>
          <div class="rounded-xl bg-primary p-10 text-on-primary md:col-span-4">
            <span class="material-symbols-outlined mb-6">language</span>
            <h3 class="font-headline text-3xl font-bold">95+ Languages</h3>
            <p class="mt-4 text-white/80">Global content at your fingertips. From Mandarin to Portuguese, our engine maintains context and dialect nuances.</p>
            <div class="mt-8 flex flex-wrap gap-2">
              ${["EN-US", "TR-TR", "ES-ES", "FR-FR", "JA-JP"].map((language) => `<span class="rounded-sm bg-white/10 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.2em]">${language}</span>`).join("")}
            </div>
          </div>
          <div class="rounded-xl bg-surface-container-highest p-10 md:col-span-4">
            <span class="material-symbols-outlined mb-6 text-primary">terminal</span>
            <h3 class="font-headline text-2xl font-bold">API & Agent Ready</h3>
            <p class="mt-4 text-sm leading-relaxed text-secondary">Integrate directly with AutoGPT, Zapier, or your custom Python agents. Webhook support included.</p>
          </div>
          <div class="rounded-xl bg-surface-container-lowest p-10 md:col-span-4">
            <span class="material-symbols-outlined mb-6 text-primary">reorder</span>
            <h3 class="font-headline text-2xl font-bold">Batch Profile Sync</h3>
            <p class="mt-4 text-sm leading-relaxed text-secondary">Input a channel or profile URL and let us scrape the entire history. Ideal for competitor research.</p>
          </div>
          <div class="rounded-xl bg-surface-container-lowest p-10 md:col-span-4">
            <span class="material-symbols-outlined mb-6 text-primary">file_download</span>
            <h3 class="font-headline text-2xl font-bold">TXT + JSON Export</h3>
            <p class="mt-4 text-sm leading-relaxed text-secondary">Download your transcripts in the format you need. Rich JSON includes speaker confidence and timestamps.</p>
          </div>
        </div>
      </div>
    </section>

    <section class="mx-auto max-w-7xl px-8 mb-32">
      <div class="flex flex-col gap-8 md:flex-row">
        <div class="flex-1 border-l-4 border-primary bg-surface-container-lowest p-12">
          <h4 class="mb-6 text-[10px] font-bold uppercase tracking-[0.22em] text-primary">Strategy 01</h4>
          <h3 class="mb-6 font-headline text-3xl font-bold">Viral Hook Mining</h3>
          <p class="leading-relaxed text-secondary">Extract the first 30 seconds of top-performing TikToks to study narrative structure and high-retention cues.</p>
        </div>
        <div class="flex-1 border-l-4 border-primary bg-surface-container-lowest p-12">
          <h4 class="mb-6 text-[10px] font-bold uppercase tracking-[0.22em] text-primary">Strategy 02</h4>
          <h3 class="mb-6 font-headline text-3xl font-bold">Competitor Research</h3>
          <p class="leading-relaxed text-secondary">Turn your competitor's entire YouTube history into a searchable text database to find content gaps and keyword trends.</p>
        </div>
        <div class="flex-1 border-l-4 border-primary bg-surface-container-lowest p-12">
          <h4 class="mb-6 text-[10px] font-bold uppercase tracking-[0.22em] text-primary">Strategy 03</h4>
          <h3 class="mb-6 font-headline text-3xl font-bold">Content Repurposing</h3>
          <p class="leading-relaxed text-secondary">Feed high-quality video transcripts into LLMs to generate newsletters, blog posts, and Twitter threads in seconds.</p>
        </div>
      </div>
    </section>

    <section id="pricing" class="mx-auto max-w-7xl px-8 mb-32">
      <div class="mb-16 text-center">
        <h2 class="mb-4 font-headline text-4xl font-bold">Simple, Volume-Based Plans</h2>
        <p class="text-secondary">Choose the tier that fits your content operation.</p>
      </div>
      <div class="grid gap-4 md:grid-cols-4">
        <div class="rounded-md border border-outline-variant/10 bg-surface-container-low p-8">
          <h4 class="mb-4 text-[10px] font-bold uppercase tracking-[0.22em]">Free</h4>
          <div class="mb-6 font-headline text-4xl font-bold">$0<span class="text-sm font-body font-normal text-secondary">/mo</span></div>
          <ul class="mb-12 space-y-3 text-sm text-secondary">
            <li class="flex gap-2"><span class="material-symbols-outlined text-[18px] text-primary">check</span>3 Transcripts / mo</li>
            <li class="flex gap-2"><span class="material-symbols-outlined text-[18px] text-primary">check</span>Standard Speed</li>
          </ul>
          <button data-action="start-flow" class="w-full rounded-sm border border-outline-variant py-2 text-sm font-bold text-on-surface">Current Plan</button>
        </div>
        <div class="z-10 scale-105 rounded-md border border-primary/20 bg-surface-container-lowest p-8 shadow-lg">
          <div class="mb-4 inline-block rounded-full bg-primary px-2 py-1 text-[8px] font-bold uppercase tracking-[0.2em] text-white">Most Popular</div>
          <h4 class="mb-4 text-[10px] font-bold uppercase tracking-[0.22em]">Starter</h4>
          <div class="mb-6 font-headline text-4xl font-bold">$29<span class="text-sm font-body font-normal text-secondary">/mo</span></div>
          <ul class="mb-12 space-y-3 text-sm text-secondary">
            <li class="flex gap-2"><span class="material-symbols-outlined text-[18px] text-primary">check</span>50 Transcripts / mo</li>
            <li class="flex gap-2"><span class="material-symbols-outlined text-[18px] text-primary">check</span>High Priority Engine</li>
            <li class="flex gap-2"><span class="material-symbols-outlined text-[18px] text-primary">check</span>JSON Export</li>
          </ul>
          <button data-action="start-flow" class="w-full rounded-sm bg-gradient-to-r from-primary to-primary-container py-2 text-sm font-bold text-white shadow-sm">Get Started</button>
        </div>
        <div class="rounded-md border border-outline-variant/10 bg-surface-container-low p-8">
          <h4 class="mb-4 text-[10px] font-bold uppercase tracking-[0.22em]">Pro</h4>
          <div class="mb-6 font-headline text-4xl font-bold">$79<span class="text-sm font-body font-normal text-secondary">/mo</span></div>
          <ul class="mb-12 space-y-3 text-sm text-secondary">
            <li class="flex gap-2"><span class="material-symbols-outlined text-[18px] text-primary">check</span>200 Transcripts / mo</li>
            <li class="flex gap-2"><span class="material-symbols-outlined text-[18px] text-primary">check</span>API Access</li>
            <li class="flex gap-2"><span class="material-symbols-outlined text-[18px] text-primary">check</span>Profile Scraping</li>
          </ul>
          <button data-action="start-flow" class="w-full rounded-sm bg-surface-container-highest py-2 text-sm font-bold text-on-surface">Upgrade</button>
        </div>
        <div class="rounded-md border border-outline-variant/10 bg-surface-container-low p-8">
          <h4 class="mb-4 text-[10px] font-bold uppercase tracking-[0.22em]">Business</h4>
          <div class="mb-6 font-headline text-4xl font-bold">$199<span class="text-sm font-body font-normal text-secondary">/mo</span></div>
          <ul class="mb-12 space-y-3 text-sm text-secondary">
            <li class="flex gap-2"><span class="material-symbols-outlined text-[18px] text-primary">check</span>Unlimited Transcripts</li>
            <li class="flex gap-2"><span class="material-symbols-outlined text-[18px] text-primary">check</span>Dedicated Support</li>
            <li class="flex gap-2"><span class="material-symbols-outlined text-[18px] text-primary">check</span>Custom Agents</li>
          </ul>
          <button data-action="start-flow" class="w-full rounded-sm bg-surface-container-highest py-2 text-sm font-bold text-on-surface">Contact Sales</button>
        </div>
      </div>
    </section>

    <section class="mx-auto max-w-3xl px-8 mb-32">
      <h2 class="mb-12 text-center font-headline text-3xl font-bold">Frequently Asked Questions</h2>
      <div class="space-y-8">
        ${[
          ["How accurate is the transcription?", "Our engine achieves 98.4% accuracy on high-quality studio audio and 94% on mobile-recorded shorts. We use specialized models for background noise cancellation."],
          ["Do you support private videos?", "No, for security and compliance, we only process publicly accessible links or manual file uploads from your device."],
          ["Can I use the API for my own app?", "Absolutely. Our Pro and Business plans include full REST API access with comprehensive documentation for developers."],
          ["Which platforms are supported?", "We currently support Instagram Reels, TikTok, YouTube, and direct file uploads. Vimeo support is in beta."],
          ["Can I transcribe YouTube videos?", "Yes. Simply paste the YouTube URL and our engine will extract the audio and transcribe it with full timestamp support."],
          ["What export formats do I get?", "We export in TXT, JSON, and Markdown formats. JSON includes rich metadata like speaker labels, confidence scores, and timestamps."],
          ["Can I use this from Codex, Claude, or my own scripts?", "Yes. Generate an API key from the dashboard and use our REST endpoints. We also provide MCP wrapper docs for Claude and tool setup instructions for Codex."],
        ]
          .map(
            ([title, answer]) => `
              <div class="border-b border-outline-variant/20 pb-6">
                <h3 class="mb-3 text-lg font-bold">${title}</h3>
                <p class="text-sm leading-relaxed text-secondary">${answer}</p>
              </div>
            `,
          )
          .join("")}
      </div>
    </section>

    <section class="mx-auto max-w-7xl px-8 mb-32">
      <div class="relative overflow-hidden rounded-2xl bg-primary px-16 py-24 text-center text-on-primary shadow-editorial">
        <div class="relative z-10 mx-auto max-w-2xl">
          <h2 class="mb-8 font-headline text-5xl font-bold leading-tight md:text-6xl">Ready to archive the digital world?</h2>
          <p class="mb-12 text-lg text-white/80">Join 2,500+ creators who use StoryToText as their knowledge ingestion layer.</p>
          <div class="flex flex-wrap items-center justify-center gap-4">
            <button data-action="start-flow" class="rounded-md bg-white px-10 py-4 text-lg font-bold text-primary transition-colors hover:bg-surface-container-lowest">Create Free Account</button>
            <button data-nav="/docs" class="rounded-md bg-white/10 px-10 py-4 text-lg font-bold text-white transition-colors hover:bg-white/20">Book a Demo</button>
          </div>
        </div>
      </div>
    </section>

    <footer class="bg-surface-container-low pb-12 pt-24">
      <div class="mx-auto max-w-7xl px-8">
        <div class="mb-24 grid grid-cols-2 gap-12 md:grid-cols-4 lg:grid-cols-6">
          <div class="col-span-2">
            <div class="mb-6 font-headline text-2xl font-bold italic text-on-surface">StoryToText</div>
            <p class="mb-6 max-w-xs text-sm leading-relaxed text-secondary">The premium archival layer for the creator economy. Turning video signals into actionable knowledge assets.</p>
            <div class="flex gap-4">
              <span class="material-symbols-outlined cursor-pointer text-secondary transition-colors hover:text-primary">share</span>
              <span class="material-symbols-outlined cursor-pointer text-secondary transition-colors hover:text-primary">public</span>
            </div>
          </div>
          <div>
            <h5 class="mb-6 text-[10px] font-bold uppercase tracking-[0.22em]">Product</h5>
            <ul class="space-y-4 text-sm text-secondary">
              <li><button class="transition-colors hover:text-primary">Transcription</button></li>
              <li><button data-nav="/docs" class="transition-colors hover:text-primary">API Documentation</button></li>
              <li><button data-nav="/pricing" class="transition-colors hover:text-primary">Pricing</button></li>
            </ul>
          </div>
          <div>
            <h5 class="mb-6 text-[10px] font-bold uppercase tracking-[0.22em]">Resources</h5>
            <ul class="space-y-4 text-sm text-secondary">
              <li><button class="transition-colors hover:text-primary">Blog</button></li>
              <li><button class="transition-colors hover:text-primary">Creator Guides</button></li>
              <li><button class="transition-colors hover:text-primary">Affiliate</button></li>
            </ul>
          </div>
          <div>
            <h5 class="mb-6 text-[10px] font-bold uppercase tracking-[0.22em]">Company</h5>
            <ul class="space-y-4 text-sm text-secondary">
              <li><button class="transition-colors hover:text-primary">Privacy Policy</button></li>
              <li><button class="transition-colors hover:text-primary">Terms of Service</button></li>
              <li><button class="transition-colors hover:text-primary">Contact</button></li>
            </ul>
          </div>
        </div>
        <div class="flex flex-col items-center justify-between border-t border-outline-variant/10 pt-12 text-[10px] uppercase tracking-[0.22em] text-secondary/60 md:flex-row">
          <p>&copy; 2024 StoryToText Inc. All rights reserved.</p>
          <p>Designed for the digital archivist.</p>
        </div>
      </div>
    </footer>
  `;

  window.setTimeout(() => {
    if (section) {
      const target = document.getElementById(section);
      target?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, 0);

  return marketingShell(content, section === "pricing" ? "pricing" : section === "resources" ? "resources" : "product");
}

function renderOnboardingIntent() {
  const selected = state.onboardingDraft.intent;
  const card = (value, icon, title, body) => `
    <button data-onboarding-intent="${value}" class="rounded-[1.5rem] border border-white/80 bg-white/85 p-6 text-left shadow-editorial transition-all hover:-translate-y-0.5 ${
      selected === value ? "ring-2 ring-primary" : ""
    }">
      <div class="grid h-12 w-12 place-items-center rounded-xl bg-primary-fixed text-primary"><span class="material-symbols-outlined">${icon}</span></div>
      <h3 class="mt-6 font-headline text-3xl">${title}</h3>
      <p class="mt-3 text-sm leading-7 text-on-surface/62">${body}</p>
    </button>
  `;

  return `
    <div class="min-h-screen bg-[radial-gradient(circle_at_right,rgba(255,219,205,0.25),transparent_34%),linear-gradient(180deg,rgba(255,255,255,0.9),rgba(255,255,255,0.7)),#fbf9f4] px-6 py-8">
      <div class="mx-auto max-w-7xl">
        <div class="flex items-center justify-between">
          <button data-nav="/" class="font-headline text-3xl italic">StoryToText</button>
          <div class="flex items-center gap-4 text-[11px] uppercase tracking-[0.22em] text-on-surface/38">
            <span>Step 01 of 03</span>
            <span class="material-symbols-outlined text-base">help</span>
          </div>
        </div>
        <div class="mt-16 grid gap-16 lg:grid-cols-[0.92fr_1.08fr]">
          <div class="max-w-xl pt-16">
            <h1 class="font-headline text-6xl leading-[0.94] tracking-tight">How will you use StoryToText?</h1>
            <p class="mt-8 text-lg leading-9 text-on-surface/62">Personalizing your workspace helps us tailor the transcription engine and AI workflows to your specific output goals.</p>
          </div>
          <div>
            <div class="grid gap-5 md:grid-cols-2">
              ${card("AI-assisted creator", "neurology", "AI-assisted creator", "I use transcripts for AI content workflows, prompt engineering, and creator research.")}
              ${card("Solo creator", "person", "Solo creator", "I transcribe my own content for repurposing, scripts, and archive management.")}
              ${card("Content studio", "dashboard_customize", "Content studio", "I batch-process competitor and client videos for an editorial pipeline.")}
              ${card("Developer", "terminal", "Developer", "I build tools, automations, and agents using the transcription API.")}
            </div>
            <form data-onboarding-intent-form class="mt-10 flex items-center justify-between">
              <p class="text-[11px] uppercase tracking-[0.22em] text-on-surface/35">Press continue to personalize the workspace</p>
              <button class="rounded-md bg-primary px-8 py-3 text-sm font-semibold text-on-primary disabled:opacity-40" ${selected ? "" : "disabled"}>Continue</button>
            </form>
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderOnboardingSource() {
  const selected = state.onboardingDraft.source_preference;
  const card = (value, icon, title, body) => `
    <button data-onboarding-source="${value}" class="rounded-[1.5rem] border border-white/80 bg-white/85 p-6 text-left shadow-editorial transition-all hover:-translate-y-0.5 ${
      selected === value ? "ring-2 ring-primary" : ""
    }">
      <div class="grid h-12 w-12 place-items-center rounded-xl bg-primary-fixed text-primary"><span class="material-symbols-outlined">${icon}</span></div>
      <h3 class="mt-6 font-headline text-3xl">${title}</h3>
      <p class="mt-3 text-sm leading-7 text-on-surface/62">${body}</p>
    </button>
  `;
  return `
    <div class="min-h-screen bg-[radial-gradient(circle_at_top_right,rgba(255,219,205,0.32),transparent_30%),#fbf9f4] px-6 py-8">
      <div class="mx-auto max-w-6xl">
        <div class="flex items-center justify-between">
          <button data-nav="/" class="font-headline text-3xl italic">StoryToText</button>
          <span class="material-symbols-outlined text-on-surface/38">help</span>
        </div>
        <div class="mx-auto mt-16 max-w-4xl text-center">
          <p class="text-[11px] font-bold uppercase tracking-[0.22em] text-primary/55">Onboarding • Stage 02</p>
          <h1 class="mt-6 font-headline text-6xl leading-[0.96] tracking-tight">Where do you find <span class="italic">your content?</span></h1>
          <p class="mx-auto mt-6 max-w-2xl text-lg leading-8 text-on-surface/62">Select your primary source of inspiration. We’ll tailor the transcription engine to match your workflow.</p>
        </div>
        <div class="mx-auto mt-16 grid max-w-5xl gap-6 md:grid-cols-2">
          ${card("single_url", "link", "Single URL", "Paste a link from Instagram, TikTok, or YouTube.")}
          ${card("profile_batch", "library_books", "Profile Batch", "Transcribe entire profiles, channels, or playlists.")}
          ${card("upload_files", "upload_file", "File Upload", "Upload your own audio and video files.")}
          ${card("api_agent", "developer_mode", "API & Agent", "Integrate transcription into your development environment.")}
        </div>
        <form data-onboarding-source-form class="mt-12 flex flex-col items-center gap-4">
          <button class="rounded-md bg-primary px-8 py-3 text-sm font-semibold text-on-primary disabled:opacity-40" ${selected ? "" : "disabled"}>Continue to setup</button>
          <div class="flex items-center gap-3 text-[11px] uppercase tracking-[0.22em] text-on-surface/35">
            <span>Step 2 of 3</span>
            <span class="h-[2px] w-8 bg-primary/20"></span>
            <span class="h-[2px] w-8 bg-primary"></span>
            <span class="h-[2px] w-8 bg-primary/20"></span>
          </div>
        </form>
      </div>
    </div>
  `;
}

function renderOnboardingFinal() {
  const settings = state.bootstrap?.settings || {};
  return `
    <div class="min-h-screen bg-surface px-6 py-8">
      <div class="mx-auto max-w-4xl">
        <div class="flex items-center justify-between">
          <button data-nav="/" class="font-headline text-3xl italic">StoryToText</button>
          <div class="flex items-center gap-3 text-[11px] uppercase tracking-[0.22em] text-on-surface/35">
            <span>Step 3 of 3</span>
            <span class="h-[2px] w-8 bg-primary/20"></span>
            <span class="h-[2px] w-8 bg-primary/20"></span>
            <span class="h-[2px] w-8 bg-primary"></span>
          </div>
        </div>
        <form data-onboarding-final-form class="mx-auto mt-12 max-w-3xl space-y-12">
          <div>
            <h1 class="font-headline text-6xl leading-tight tracking-tight">Final Touches</h1>
            <p class="mt-5 max-w-xl text-lg leading-8 text-on-surface/62">Customize how StoryToText adapts to your workflow. These settings ensure your archival process is as seamless as a printed page.</p>
          </div>
          <section>
            <p class="text-[10px] font-bold uppercase tracking-[0.22em] text-primary/55">01 — Linguistic Foundation</p>
            <div class="mt-5 rounded-[1.4rem] bg-white/80 p-6 shadow-editorial">
              <label for="onboarding-default-language" class="block text-[11px] font-bold uppercase tracking-[0.22em] text-on-surface/42">Default transcription language</label>
              <select id="onboarding-default-language" name="default_language" class="mt-4 w-full rounded-xl border-none bg-surface-container-low px-4 py-4 text-sm focus:ring-1 focus:ring-primary">
                ${LANGUAGE_OPTIONS.map(([value, label]) => `<option value="${value}" ${settings.default_language === value ? "selected" : ""}>${label}</option>`).join("")}
              </select>
            </div>
          </section>
          <section>
            <p class="text-[10px] font-bold uppercase tracking-[0.22em] text-primary/55">02 — Delivery & Updates</p>
            <div class="mt-5 space-y-4 rounded-[1.4rem] bg-white/80 p-6 shadow-editorial">
              <label class="flex items-center justify-between gap-4 rounded-xl bg-surface-container-low px-5 py-4">
                <div>
                  <p class="font-semibold text-on-surface">Email me when jobs are complete</p>
                  <p class="mt-1 text-sm text-on-surface/55">Receive a direct link to your transcript as soon as processing finishes.</p>
                </div>
                <input name="email_on_complete" type="checkbox" class="h-5 w-5 rounded-full border-outline-variant text-primary focus:ring-primary" ${settings.email_on_complete ? "checked" : ""} />
              </label>
              <label class="flex items-center justify-between gap-4 rounded-xl bg-surface-container-low px-5 py-4">
                <div>
                  <p class="font-semibold text-on-surface">Receive product updates</p>
                  <p class="mt-1 text-sm text-on-surface/55">Stay informed about new archival features and editorial improvements.</p>
                </div>
                <input name="product_updates" type="checkbox" class="h-5 w-5 rounded-full border-outline-variant text-primary focus:ring-primary" ${settings.product_updates ? "checked" : ""} />
              </label>
            </div>
          </section>
          <div class="overflow-hidden rounded-[1.6rem] bg-[linear-gradient(120deg,rgba(27,28,25,0.76),rgba(255,255,255,0.82)),radial-gradient(circle_at_top_right,rgba(255,181,150,0.32),transparent_30%)] px-6 py-12 text-white shadow-editorial">
            <p class="text-[11px] uppercase tracking-[0.22em] text-white/55">Workspace Preview</p>
            <h3 class="mt-5 max-w-xl font-headline text-4xl">An editorial control room for turning media into durable language.</h3>
          </div>
          <div class="flex items-center justify-between">
            <button type="button" data-nav="/onboarding/source" class="text-sm font-medium text-on-surface/55 transition-colors hover:text-primary">← Previous step</button>
            <button class="rounded-md bg-primary px-8 py-3 text-sm font-semibold text-on-primary">Go to dashboard</button>
          </div>
        </form>
      </div>
    </div>
  `;
}

function renderDashboard() {
  const billing = state.bootstrap.billing;
  const jobs = state.bootstrap.jobs.slice(0, 5);
  const rows = jobs
    .map(
      (job) => `
      <tr class="table-hover-row text-sm">
        <td class="px-8 py-5">
          <div class="flex items-center gap-3">
            <span class="material-symbols-outlined text-primary/40">description</span>
            <div>
              <p class="font-medium text-on-surface">${escapeHtml(job.title)}</p>
              <p class="mt-1 text-[0.7rem] text-on-surface/40">${escapeHtml(job.id)}</p>
            </div>
          </div>
        </td>
        <td class="px-4 py-5 text-on-surface/65">
          <div class="flex items-center gap-3">
            <span class="material-symbols-outlined text-on-surface/35">${sourceIcon(job)}</span>
            <span>${escapeHtml(job.platform_label || job.platform || "Source")}</span>
          </div>
        </td>
        <td class="px-4 py-5 text-center">${statusBadge(job)}</td>
        <td class="px-4 py-5 text-on-surface/55">${formatDateTime(job.created_at)}</td>
        <td class="px-8 py-5 text-right">
          ${
            normalizedJobStatus(job) === "failed"
              ? `<button data-retry-job="${job.id}" class="inline-flex items-center gap-1 font-semibold text-error"><span class="material-symbols-outlined text-lg">refresh</span>Retry</button>`
              : `<button data-nav="/transcripts/${job.id}" class="inline-flex items-center gap-1 font-semibold text-primary"><span class="material-symbols-outlined text-lg">visibility</span>View</button>`
          }
        </td>
      </tr>
    `,
    )
    .join("");

  return appShell(
    "dashboard",
    "Dashboard",
    `
      <div class="mx-auto max-w-6xl space-y-12">
        <section class="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div class="max-w-xl">
            <h3 class="font-headline text-5xl leading-tight">Welcome back, Archivist.</h3>
            <p class="mt-2 text-[0.95rem] leading-relaxed text-on-surface-variant">Your studio is ready. Ready to transform your spoken stories into timeless text records?</p>
          </div>
          <button data-nav="/new" class="inline-flex items-center gap-3 rounded-md bg-gradient-to-br from-primary to-primary-container px-8 py-4 font-bold text-on-primary shadow-editorial transition-transform hover:scale-[1.01] active:scale-[0.98]">
            <span class="material-symbols-outlined" style="font-variation-settings:'FILL' 1">add_circle</span>
            <span>New Transcription</span>
          </button>
        </section>

        <section class="grid gap-8 md:grid-cols-12">
          <div class="rounded-xl bg-surface-container-low p-8 md:col-span-8">
            <div class="mb-6 flex items-start justify-between">
              <div>
                <span class="text-[0.75rem] uppercase tracking-[0.2em] text-on-surface/55">Usage Overview</span>
                <h4 class="mt-1 font-headline text-[1.8rem] italic">Credits & Minutes Used</h4>
              </div>
              <span class="material-symbols-outlined text-primary-container">speed</span>
            </div>
            <div class="space-y-6">
              <div>
                <div class="mb-2 flex justify-between">
                  <span class="text-base font-semibold text-on-surface">${billing.minutes_used} <span class="font-normal text-on-surface/50">/ ${billing.minutes_limit} min</span></span>
                  <span class="text-sm font-bold text-primary">${billing.usage_pct}%</span>
                </div>
                <div class="h-3 overflow-hidden rounded-full bg-surface-container-highest">
                  <div class="h-full rounded-full bg-primary" style="width:${Math.min(billing.usage_pct, 100)}%"></div>
                </div>
              </div>
              <div class="grid grid-cols-2 gap-8">
                <div class="rounded-lg bg-surface p-4">
                  <p class="mb-1 text-[0.75rem] uppercase tracking-[0.18em] text-on-surface/55">Web Platform</p>
                  <p class="text-2xl font-bold">${billing.web_minutes} min</p>
                </div>
                <div class="rounded-lg bg-surface p-4">
                  <p class="mb-1 text-[0.75rem] uppercase tracking-[0.18em] text-on-surface/55">API Integration</p>
                  <p class="text-2xl font-bold">${billing.api_minutes} min</p>
                </div>
              </div>
            </div>
          </div>
          <div class="relative overflow-hidden rounded-xl bg-primary-container p-8 text-on-primary md:col-span-4">
            <div class="relative z-10">
              <span class="text-[0.75rem] uppercase tracking-[0.2em] text-primary-fixed">Dev Health</span>
              <h4 class="mt-4 font-headline text-3xl">API Response Rate</h4>
              <p class="mb-4 mt-4 font-headline text-6xl font-bold">${state.bootstrap.health.response_rate}%</p>
              <p class="leading-relaxed text-white/90">Your custom endpoints are performing optimally with a ${state.bootstrap.health.avg_latency_ms}ms average latency.</p>
            </div>
            <div class="absolute -bottom-10 -right-10 h-40 w-40 rounded-full bg-white/5 transition-transform duration-700 hover:scale-110"></div>
          </div>
        </section>

        <section class="mb-12">
          <div class="mb-8 flex items-baseline justify-between">
            <h3 class="font-headline text-3xl">Recent Jobs</h3>
            <button data-nav="/history" class="text-sm font-bold text-primary hover:underline">View All Records</button>
          </div>
          <div class="overflow-hidden rounded-xl bg-white shadow-editorial">
            <table class="min-w-full text-left">
              <thead class="bg-surface-container-low text-[0.7rem] font-bold uppercase tracking-[0.2em] text-on-surface/50">
                <tr>
                  <th class="px-8 py-4">Transcription Name</th>
                  <th class="px-4 py-4">Platform</th>
                  <th class="px-4 py-4 text-center">Status</th>
                  <th class="px-4 py-4">Created</th>
                  <th class="px-8 py-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-surface-container">${rows}</tbody>
            </table>
          </div>
        </section>
      </div>
    `,
  );
}

function formSelect(name, value, options) {
  return `
    <select name="${name}" class="w-full rounded-lg border-none bg-surface-container-lowest px-4 py-4 text-sm ring-1 ring-outline-variant/20 focus:ring-primary">
      ${options.map(([itemValue, label]) => `<option value="${itemValue}" ${value === itemValue ? "selected" : ""}>${label}</option>`).join("")}
    </select>
  `;
}

function renderNewTranscription() {
  const mode = state.form.mode;
  const tab = (id, label) => `
    <button data-transcription-tab="${id}" class="rounded-md px-6 py-2.5 text-sm transition-colors ${
      mode === id ? "bg-white text-primary shadow-sm font-semibold" : "text-on-surface/60 hover:text-on-surface"
    }">${label}</button>
  `;

  const singleUrlFields = `
    <div class="space-y-2">
      <label class="ml-1 text-[0.7rem] uppercase tracking-[0.22em] text-on-surface/45">Media source</label>
      <div class="group relative">
        <input name="source_value" value="${escapeHtml(state.form.source_value)}" class="w-full rounded-lg border-none bg-surface-container-lowest px-6 py-5 font-headline text-lg italic text-on-surface ring-1 ring-outline-variant/20 placeholder:text-on-surface/20 focus:ring-primary" placeholder="https://youtube.com/watch?v=..." />
        <span class="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 text-on-surface/40">video_library</span>
      </div>
      <p class="flex items-center gap-2 px-1 text-[0.75rem] italic text-on-surface/40"><span class="material-symbols-outlined text-xs">auto_awesome</span>Auto-detecting YouTube, TikTok, and Reels formatting...</p>
    </div>
  `;

  const batchFields = `
    <div class="grid gap-6 md:grid-cols-[0.36fr_1fr]">
      <div class="space-y-2">
        <label class="ml-1 text-[0.7rem] uppercase tracking-[0.22em] text-on-surface/45">Platform</label>
        ${formSelect("platform_hint", state.form.platform_hint, [
          ["youtube", "YouTube"],
          ["instagram", "Instagram"],
          ["tiktok", "TikTok"],
        ])}
      </div>
      <div class="space-y-2">
        <label class="ml-1 text-[0.7rem] uppercase tracking-[0.22em] text-on-surface/45">Channel, handle, or playlist</label>
        <input name="source_value" value="${escapeHtml(state.form.source_value)}" class="w-full rounded-lg border-none bg-surface-container-lowest px-6 py-5 font-headline text-lg italic text-on-surface ring-1 ring-outline-variant/20 placeholder:text-on-surface/20 focus:ring-primary" placeholder="@creator or playlist URL" />
      </div>
    </div>
  `;

  const uploadFields = `
    <div class="space-y-2">
      <label class="ml-1 text-[0.7rem] uppercase tracking-[0.22em] text-on-surface/45">Upload media files</label>
      <input name="media" type="file" multiple class="w-full rounded-xl border border-dashed border-outline-variant/35 bg-white/85 px-6 py-10 text-sm text-on-surface/55 file:mr-4 file:rounded-md file:border-0 file:bg-primary file:px-4 file:py-2 file:text-sm file:font-semibold file:text-on-primary hover:border-primary/35" />
    </div>
  `;

  return appShell(
    "new",
    "New Transcription",
    `
      <div class="mx-auto max-w-6xl">
        <div class="mb-12 flex justify-start">
          <div class="flex gap-1 rounded-lg bg-surface-container-low p-1.5 shadow-sm">
            ${tab("single_url", "Single URL")}
            ${tab("profile_batch", "Profile Batch")}
            ${tab("upload_files", "Upload Files")}
          </div>
        </div>
        <div class="grid gap-16 lg:grid-cols-12">
          <form data-new-job-form class="space-y-10 lg:col-span-7">
            ${mode === "single_url" ? singleUrlFields : mode === "profile_batch" ? batchFields : uploadFields}
            <div class="grid gap-6 md:grid-cols-2">
              <div class="space-y-2">
                <label class="ml-1 text-[0.7rem] uppercase tracking-[0.22em] text-on-surface/45">Language</label>
                ${formSelect("language", state.form.language, LANGUAGE_OPTIONS)}
              </div>
              <div class="space-y-2">
                <label class="ml-1 text-[0.7rem] uppercase tracking-[0.22em] text-on-surface/45">Model</label>
                ${formSelect("model", state.form.model, MODEL_OPTIONS)}
              </div>
            </div>
            <label class="flex items-center justify-between gap-4 rounded-lg bg-surface-container-low px-5 py-4">
              <div>
                <p class="font-semibold text-on-surface">Identify speakers</p>
                <p class="text-sm text-on-surface/55">Speaker separation is stored as a workflow preference for future processing.</p>
              </div>
              <div class="relative">
                <input name="speaker_detection" type="checkbox" class="switch-input sr-only" ${state.form.speaker_detection ? "checked" : ""}/>
                <div class="switch peer-checked:bg-primary" data-on="${state.form.speaker_detection ? "true" : "false"}"></div>
              </div>
            </label>
            <button class="w-full rounded-md bg-gradient-to-r from-primary to-primary-container px-6 py-5 text-sm font-bold uppercase tracking-[0.24em] text-on-primary shadow-editorial">Transcribe now</button>
            <div class="rounded-xl bg-surface-container-low p-8">
              <div class="flex items-start gap-4">
                <div class="rounded bg-primary-fixed p-2 text-primary"><span class="material-symbols-outlined">bolt</span></div>
                <div>
                  <h4 class="font-headline text-lg italic">Pro tip: Batch processing</h4>
                  <p class="mt-2 text-sm leading-relaxed text-on-surface/62">Need to transcribe an entire channel? Switch to <strong>Profile Batch</strong> to pull all recent uploads in one command.</p>
                </div>
              </div>
            </div>
          </form>
          <div class="lg:col-span-5">
            <div class="sticky top-32 space-y-12">
              <div class="relative aspect-[4/5] overflow-hidden rounded-xl bg-on-surface p-10 text-surface shadow-editorial">
                <div class="absolute -right-32 -top-32 h-64 w-64 bg-primary/20 blur-[100px]"></div>
                <div class="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,181,150,0.2),transparent_30%),linear-gradient(180deg,rgba(0,0,0,0.1),rgba(0,0,0,0.45))]"></div>
                <div class="relative z-10 flex h-full flex-col justify-between">
                  <div class="space-y-4">
                    <span class="rounded-full bg-white/10 px-3 py-1 text-[0.6rem] uppercase tracking-[0.3em] backdrop-blur-sm">Editor's Choice</span>
                    <h3 class="font-headline text-3xl leading-tight">Analyze a viral video</h3>
                    <p class="max-w-[240px] text-sm leading-relaxed text-surface/60">Deeply understand content structures and hooks. Feed our results directly into your AI creative workflow.</p>
                  </div>
                  <button data-nav="/docs" class="inline-flex items-center gap-2 border-b border-primary/40 pb-1 text-xs uppercase tracking-[0.22em] text-white/80 transition-colors hover:text-primary-fixed">
                    Explore the playbook
                    <span class="material-symbols-outlined text-sm">arrow_forward</span>
                  </button>
                </div>
              </div>
              <div class="space-y-8 border-l border-outline-variant/20 pl-6">
                <div>
                  <h5 class="font-headline text-xl italic">Instant Accuracy</h5>
                  <p class="mt-3 text-sm leading-relaxed text-on-surface/50">Our Digital Archivist engine preserves nuanced speech patterns, filler words, and technical jargon with production-ready structure.</p>
                </div>
                <div>
                  <h5 class="font-headline text-xl italic">Workflow Integration</h5>
                  <p class="mt-3 text-sm leading-relaxed text-on-surface/50">Export directly to Notion, Obsidian, or Markdown. Perfect for researchers and heavy-duty content creators.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `,
  );
}

function stepper(job) {
  const numericProgress = Number(job.progress || 0);
  const resolvedIndex =
    job.status === "failed"
      ? Math.min(PHASES.length - 2, Math.max(0, Math.round(numericProgress * (PHASES.length - 1))))
      : Math.max(PHASES.indexOf(job.phase), job.status === "completed" ? PHASES.length - 1 : 0);
  return `
    <div class="rounded-[1.6rem] bg-white/75 p-8 shadow-editorial">
      <div class="relative">
        <div class="absolute left-0 right-0 top-5 h-[2px] bg-outline-variant/30"></div>
        <div class="absolute left-0 top-5 h-[2px] ${job.status === "failed" ? "bg-error" : "bg-primary"}" style="width:${(Math.min(resolvedIndex, PHASES.length - 1) / (PHASES.length - 1)) * 100}%"></div>
        <div class="relative grid grid-cols-6 gap-2">
          ${PHASES.map((phase, index) => {
            const done = index < resolvedIndex || (job.status === "completed" && index === resolvedIndex);
            const active = index === resolvedIndex && job.status !== "completed";
            return `
              <div class="timeline-step ${active ? "active" : ""} flex flex-col items-center gap-4 text-center">
                <div class="step-bullet grid h-10 w-10 place-items-center rounded-full ${
                  done
                    ? job.status === "failed" && index === resolvedIndex
                      ? "bg-error text-on-error"
                      : "bg-primary text-on-primary"
                    : active
                      ? job.status === "failed"
                        ? "border-2 border-error bg-error-container text-on-error-container"
                        : "border-2 border-primary bg-primary-fixed text-primary"
                      : "border border-outline-variant/30 bg-surface-container-highest text-on-surface/35"
                }">
                  <span class="material-symbols-outlined text-lg">${
                    job.status === "failed" && index === resolvedIndex
                      ? "close"
                      : done
                        ? "check"
                        : active
                          ? "sync"
                          : "pending"
                  }</span>
                </div>
                <span class="text-[10px] font-bold uppercase tracking-[0.18em] ${
                  active ? (job.status === "failed" ? "text-error" : "text-primary") : "text-on-surface/45"
                }">${phase.replace("_", " ")}</span>
              </div>
            `;
          }).join("")}
        </div>
      </div>
    </div>
  `;
}

function renderJobProcessing(jobId) {
  const job = state.bootstrap.jobs.find((item) => item.id === jobId);
  if (!job) return appShell("new", "Job Processing", `<div class="rounded-3xl bg-white/80 p-8 shadow-editorial">Job not found.</div>`);
  const eta = Math.max(6, Math.round((1 - Number(job.progress || 0)) * 120));
  const buttonRow =
    job.status === "completed"
      ? `<button data-nav="/transcripts/${job.id}" class="rounded-md bg-primary px-6 py-3 text-sm font-semibold text-on-primary">View transcript</button>`
      : job.status === "failed"
        ? `<button data-retry-job="${job.id}" class="rounded-md bg-primary px-6 py-3 text-sm font-semibold text-on-primary">Retry job</button>`
        : `<button data-nav="/dashboard" class="inline-flex items-center gap-2 rounded-md bg-surface-container-low px-6 py-3 text-sm font-semibold text-on-surface"><span class="material-symbols-outlined text-base">arrow_back</span>Back to Dashboard</button>`;

  return appShell(
    "new",
    "Job Processing",
    `
      <div class="mx-auto max-w-5xl space-y-8">
        <section class="relative overflow-hidden rounded-[1.6rem] bg-white/80 p-8 shadow-editorial">
          <div class="absolute right-0 top-0 h-full w-1/3 -skew-x-12 bg-primary/5 translate-x-1/3"></div>
          <div class="relative z-10 flex flex-col gap-8 md:flex-row md:items-end md:justify-between">
            <div>
              <p class="text-[11px] font-bold uppercase tracking-[0.22em] text-primary/55">Current active task</p>
              <h3 class="mt-4 max-w-3xl font-instrument text-5xl leading-none text-on-surface">${escapeHtml(job.title)}</h3>
              <p class="mt-4 flex items-center gap-2 text-sm text-on-surface/55"><span class="material-symbols-outlined text-sm">link</span>${escapeHtml(job.source_value || "Direct upload")}</p>
            </div>
            <div class="text-right">
              <div class="flex items-center justify-end gap-2 text-primary">
                <span class="material-symbols-outlined text-base">schedule</span>
                <span class="text-3xl font-semibold">${eta}</span>
                <span class="text-xs font-bold uppercase tracking-[0.18em]">seconds left</span>
              </div>
              <p class="mt-2 text-xs italic text-on-surface/45">Estimated completion time</p>
            </div>
          </div>
        </section>
        ${stepper(job)}
        <section class="grid gap-6 lg:grid-cols-[0.72fr_1fr]">
          <div class="space-y-5">
            <div class="rounded-[1.4rem] border-l-4 border-primary bg-primary-fixed/35 p-6 shadow-editorial">
              <p class="flex items-start gap-3 text-sm leading-8 text-on-primary-fixed-variant"><span class="material-symbols-outlined mt-1 text-base text-primary">info</span>You can leave this page and find the job in <strong>History</strong> once processing completes.</p>
            </div>
            <div class="flex flex-wrap gap-3">${buttonRow}
              ${job.status === "completed" ? `<a href="/downloads/${job.id}.txt" class="rounded-md border border-outline-variant/35 px-5 py-3 text-sm font-semibold text-on-surface/65">Download TXT</a>` : ""}
            </div>
            ${job.error ? `<div class="rounded-[1.4rem] bg-error-container p-6 text-sm text-on-error-container shadow-editorial">${escapeHtml(job.error)}</div>` : ""}
          </div>
          <div class="overflow-hidden rounded-[1.6rem] shadow-editorial">
            <div class="relative aspect-[16/9] bg-[radial-gradient(circle_at_top_right,rgba(218,193,184,0.45),transparent_40%),linear-gradient(135deg,rgba(234,232,227,0.9),rgba(245,243,238,1))]">
              <div class="absolute inset-0 flex items-center justify-center">
                <div class="h-40 w-40 rounded-full bg-white/50 shadow-lg backdrop-blur-md"></div>
                <div class="absolute h-28 w-28 rounded-full bg-surface-container-highest/70 shadow-md"></div>
              </div>
            </div>
            <div class="bg-white/82 p-8">
              <p class="inline-flex rounded-full bg-primary-fixed px-3 py-1 text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Pro Tip</p>
              <h4 class="mt-5 font-headline text-3xl leading-tight text-on-surface">Leverage our API for bulk transcription workflows.</h4>
              <div class="mt-8 grid gap-4 md:grid-cols-2">
                <div class="rounded-2xl bg-surface-container-low p-5">
                  <p class="text-[11px] uppercase tracking-[0.22em] text-on-surface/45">Audio quality</p>
                  <div class="mt-4 h-2 rounded-full bg-surface-container-highest"><div class="h-full w-4/5 rounded-full bg-primary"></div></div>
                  <p class="mt-4 text-sm text-on-surface/55">High Fidelity (48 kHz)</p>
                </div>
                <div class="rounded-2xl bg-surface-container-low p-5">
                  <p class="text-[11px] uppercase tracking-[0.22em] text-on-surface/45">Security level</p>
                  <div class="mt-4 flex items-center gap-2">
                    <span class="material-symbols-outlined text-base text-primary">lock</span>
                    <span class="text-sm font-medium text-on-surface">End-to-End Encrypted</span>
                  </div>
                  <p class="mt-3 text-sm text-on-surface/55">ISO 27001 Certified</p>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    `,
    "Processing",
  );
}

function filteredJobs() {
  const query = state.historyQuery.trim().toLowerCase();
  return state.bootstrap.jobs.filter((job) => {
    const matchesFilter = state.historyFilter === "all" || normalizedJobStatus(job) === state.historyFilter;
    const haystack = `${job.title} ${job.platform_label} ${job.source_value}`.toLowerCase();
    return matchesFilter && (!query || haystack.includes(query));
  });
}

function renderHistory() {
  const allJobs = filteredJobs();
  const totalJobs = allJobs.length;
  const totalPages = Math.max(1, Math.ceil(totalJobs / state.historyPerPage));
  state.historyPage = Math.min(state.historyPage, totalPages);
  const startIdx = (state.historyPage - 1) * state.historyPerPage;
  const endIdx = Math.min(startIdx + state.historyPerPage, totalJobs);
  const jobs = allJobs.slice(startIdx, endIdx);

  const pill = (value, label) => `
    <button data-history-filter="${value}" class="pb-2 text-[0.7rem] font-bold uppercase tracking-[0.22em] transition-colors ${
      state.historyFilter === value
        ? "border-b-2 border-primary text-primary"
        : "border-b-2 border-transparent text-on-surface/40 hover:text-on-surface"
    }">${label}</button>
  `;

  const paginationBtn = (page, label, isCurrent) => `
    <button data-history-page="${page}" class="grid h-9 w-9 place-items-center rounded-md text-sm font-semibold transition-colors ${
      isCurrent ? "bg-primary text-on-primary" : "text-on-surface/50 hover:bg-surface-container-high"
    }">${label}</button>
  `;

  let paginationHtml = "";
  if (totalPages > 1) {
    const pages = [];
    for (let i = 1; i <= totalPages; i++) pages.push(paginationBtn(i, i, i === state.historyPage));
    paginationHtml = `
      <div class="mt-8 flex items-center justify-between">
        <p class="text-sm text-on-surface/40">Showing ${startIdx + 1}–${endIdx} of ${totalJobs} transcription jobs</p>
        <div class="flex items-center gap-1">
          ${state.historyPage > 1 ? `<button data-history-page="${state.historyPage - 1}" class="grid h-9 w-9 place-items-center rounded-md text-on-surface/40 hover:bg-surface-container-high"><span class="material-symbols-outlined text-lg">chevron_left</span></button>` : ""}
          ${pages.join("")}
          ${state.historyPage < totalPages ? `<button data-history-page="${state.historyPage + 1}" class="grid h-9 w-9 place-items-center rounded-md text-on-surface/40 hover:bg-surface-container-high"><span class="material-symbols-outlined text-lg">chevron_right</span></button>` : ""}
        </div>
      </div>
    `;
  }

  return appShell(
    "history",
    "History",
    `
      <div class="mx-auto max-w-6xl">
        <p class="mb-8 text-[11px] uppercase tracking-[0.22em] text-on-surface/40">Archive of all past transcriptions</p>
        <section class="px-2 pb-20">
          <div class="mb-12 flex flex-col gap-8 md:flex-row md:items-end md:justify-between">
            <div class="flex gap-8 border-b border-outline-variant/10 pb-2">
              ${pill("all", "All")}
              ${pill("completed", "Completed")}
              ${pill("processing", "Processing")}
              ${pill("failed", "Failed")}
            </div>
            <div class="flex items-center gap-4">
              <div class="relative w-full md:w-80">
                <span class="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface/30 text-lg">search</span>
                <input id="history-search" value="${escapeHtml(state.historyQuery)}" class="w-full rounded-md border border-outline-variant/20 bg-white py-3 pl-12 pr-4 text-sm placeholder:text-on-surface/30 focus:border-primary/40 focus:outline-none" placeholder="Search by job name..." />
              </div>
              <button data-action="invoice-toast" class="hidden items-center gap-2 rounded-md bg-surface-container-high px-4 py-3 text-sm font-semibold text-on-surface transition-colors hover:bg-surface-container-highest md:inline-flex"><span class="material-symbols-outlined text-base">download</span>Export</button>
            </div>
          </div>

          ${
            totalJobs
              ? `
                <div class="overflow-hidden rounded-xl bg-surface-container-low shadow-editorial">
                  <table class="min-w-full text-left">
                    <thead>
                      <tr class="bg-surface-container-high/50 text-[0.65rem] uppercase tracking-[0.22em] text-on-surface/50">
                        <th class="px-8 py-5">Job Name</th>
                        <th class="px-6 py-5">Source</th>
                        <th class="px-6 py-5 text-center">Status</th>
                        <th class="px-6 py-5">Created At</th>
                        <th class="px-6 py-5">Duration</th>
                        <th class="px-6 py-5">Origin</th>
                        <th class="px-8 py-5 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody id="history-list" class="divide-y divide-outline-variant/10">
                      ${jobs
                        .map(
                          (job) => `
                            <tr data-history-item data-status="${escapeHtml(normalizedJobStatus(job))}" data-haystack="${escapeHtml(`${job.title} ${job.platform_label} ${job.source_value}`.toLowerCase())}" class="table-hover-row group">
                              <td class="px-8 py-6">
                                <p class="font-headline text-lg leading-tight text-on-surface">${escapeHtml(job.title)}</p>
                                <p class="mt-1 text-[0.7rem] text-on-surface/40">ID: ${escapeHtml(job.id)}</p>
                              </td>
                              <td class="px-6 py-6">
                                <div class="flex items-center gap-3">
                                  <span class="material-symbols-outlined text-primary/60">${sourceIcon(job)}</span>
                                  <span class="text-sm">${escapeHtml(job.platform_label || job.platform || "Source")}</span>
                                </div>
                              </td>
                              <td class="px-6 py-6 text-center">${statusBadge(job)}</td>
                              <td class="px-6 py-6 text-sm text-on-surface/70">${formatDateTime(job.created_at)}</td>
                              <td class="px-6 py-6 text-sm font-medium">${job.duration_minutes ? formatMinutes(job.duration_minutes) : "—"}</td>
                              <td class="px-6 py-6">
                                <span class="material-symbols-outlined text-on-surface/30" title="${escapeHtml(jobOriginLabel(job))}">${jobOriginIcon(job)}</span>
                              </td>
                              <td class="px-8 py-6 text-right">
                                ${
                                  normalizedJobStatus(job) === "failed"
                                    ? `<button data-retry-job="${job.id}" class="inline-flex items-center gap-1 text-error transition-colors hover:opacity-80"><span class="material-symbols-outlined text-lg">refresh</span></button>`
                                    : normalizedJobStatus(job) === "processing"
                                      ? `<span class="text-xs italic text-on-surface/40">In queue...</span>`
                                      : `<div class="flex justify-end gap-3 opacity-100 transition-opacity md:opacity-0 md:group-hover:opacity-100">
                                          <button data-nav="/transcripts/${job.id}" class="rounded p-2 text-on-surface/60 transition-colors hover:bg-surface-container-high hover:text-primary"><span class="material-symbols-outlined text-lg">visibility</span></button>
                                          <a href="/downloads/${job.id}.txt" class="rounded p-2 text-on-surface/60 transition-colors hover:bg-surface-container-high hover:text-primary"><span class="material-symbols-outlined text-lg">download</span></a>
                                        </div>`
                                }
                              </td>
                            </tr>
                          `,
                        )
                        .join("")}
                    </tbody>
                  </table>
                </div>
                ${paginationHtml}
                <div id="history-empty" style="display:none" class="mt-12 rounded-2xl border border-dashed border-outline-variant/30 bg-white/60 px-8 py-24 text-center">
                  <h3 class="font-headline text-2xl text-on-surface">No transcription jobs found</h3>
                  <p class="mx-auto mt-4 max-w-sm text-on-surface/50">It looks like your archive is currently empty. Start your first transcription to see it appear here.</p>
                  <button data-nav="/new" class="mt-8 inline-flex items-center gap-2 rounded-md bg-primary px-8 py-3 font-medium text-on-primary transition-opacity hover:opacity-90">
                    <span class="material-symbols-outlined">add</span>
                    Create New Job
                  </button>
                </div>
              `
              : `
                <div id="history-empty" class="mt-12 rounded-2xl border border-dashed border-outline-variant/30 bg-white/60 px-8 py-24 text-center">
                  <h3 class="font-headline text-2xl text-on-surface">No transcription jobs found</h3>
                  <p class="mx-auto mt-4 max-w-sm text-on-surface/50">It looks like your archive is currently empty. Start your first transcription to see it appear here.</p>
                  <button data-nav="/new" class="mt-8 inline-flex items-center gap-2 rounded-md bg-primary px-8 py-3 font-medium text-on-primary transition-opacity hover:opacity-90">
                    <span class="material-symbols-outlined">add</span>
                    Create New Job
                  </button>
                </div>
              `
          }
        </section>
      </div>
    `,
  );
}

function renderTranscriptDetail(jobId) {
  const job = state.bootstrap.jobs.find((item) => item.id === jobId);
  if (!job) return appShell("history", "Transcript Detail", `<div class="rounded-3xl bg-white/80 p-8 shadow-editorial">Transcript not found.</div>`);
  const first = job.results?.[0] || {};
  const blocks = (job.results || [])
    .map((result, index) => {
      const chunks = result.chunks?.length ? result.chunks : [{ timestamp: [0, 0], text: result.transcription || "" }];
      return `
        <section class="${index ? "mt-16 pt-12 border-t border-outline-variant/15" : ""}">
          ${job.results.length > 1 ? `<h3 class="mb-8 font-headline text-3xl">${escapeHtml(result.caption || result.filename || `Item ${index + 1}`)}</h3>` : ""}
          <div class="prose-transcript space-y-10 text-lg leading-9 text-on-surface/90">
            ${chunks
              .map(
                (chunk, chunkIndex) => `
                  <div>
                    <span class="mb-3 block text-[10px] font-bold uppercase tracking-[0.22em] text-primary/40">Page ${String(chunkIndex + 1).padStart(2, '0')} &mdash; ${escapeHtml(formatChunkRange(chunk.timestamp))}</span>
                    <p>${escapeHtml(chunk.text || "")}</p>
                    ${
                      chunkIndex === 1
                        ? `<blockquote class="my-12 border-l-2 border-primary-fixed pl-8 font-headline text-2xl italic leading-snug text-on-surface-variant md:text-3xl"><em>"The machine provides the vocabulary, but the human provides the heartbeat. That is the fundamental contract of the new creative era."</em></blockquote>`
                        : ""
                    }
                  </div>
                `,
              )
              .join("")}
          </div>
        </section>
      `;
    })
    .join("");

  return appShell(
    "history",
    "Transcript Detail",
    `
      <div class="mx-auto max-w-6xl">
        <section class="max-w-6xl px-2 pb-2 pt-2">
          <div class="flex items-start justify-between gap-12">
            <div class="flex-1">
              <div class="mb-6 flex items-center gap-3">
                <div class="flex h-8 w-8 items-center justify-center rounded-full bg-error-container">
                  <span class="material-symbols-outlined text-lg text-on-error-container" style="font-variation-settings:'FILL' 1">play_circle</span>
                </div>
                <span class="text-xs uppercase tracking-[0.2em] text-on-surface-variant/70">${escapeHtml(job.platform_label || "Source")} Source</span>
              </div>
              <h2 class="font-instrument text-5xl leading-tight text-on-surface">${escapeHtml(job.title)}</h2>
              <p class="mt-4 text-sm text-on-surface/50">Created on ${formatDateTime(job.created_at)}</p>
            </div>
            <div class="hidden w-48 overflow-hidden rounded-xl shadow-sm lg:block">
              <div class="aspect-video bg-[radial-gradient(circle_at_30%_30%,rgba(0,114,128,0.6),rgba(0,88,99,0.8)),linear-gradient(135deg,rgba(0,88,99,0.9),rgba(0,114,128,0.7))]">
                <div class="flex h-full items-center justify-center">
                  <span class="material-symbols-outlined text-4xl text-white/60" style="font-variation-settings:'FILL' 1">play_circle</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <div class="sticky top-20 z-20 mt-8 border-b border-outline-variant/10 bg-surface/80 px-2 py-4 backdrop-blur-md">
          <div class="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4">
            <div class="flex flex-wrap items-center gap-4">
              <button data-copy-job="${job.id}" class="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-on-primary shadow-md transition-colors hover:bg-primary-container">
                <span class="material-symbols-outlined text-lg">content_copy</span>
                Copy transcript
              </button>
              <div class="mx-2 hidden h-6 w-px bg-outline-variant/30 md:block"></div>
              <a href="/downloads/${job.id}.txt" class="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-on-surface-variant transition-colors hover:bg-surface-container-high">
                <span class="material-symbols-outlined text-lg text-primary">description</span>
                Download TXT
              </a>
              <a href="/downloads/${job.id}.json" class="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-on-surface-variant transition-colors hover:bg-surface-container-high">
                <span class="material-symbols-outlined text-lg text-primary">data_object</span>
                Download JSON
              </a>
            </div>
            <button data-retry-job="${job.id}" class="flex items-center gap-2 rounded-lg border border-outline-variant/40 px-4 py-2 text-sm font-medium text-on-surface-variant transition-all hover:border-primary/40">
              <span class="material-symbols-outlined text-lg">refresh</span>
              Re-run
            </button>
          </div>
        </div>

        <div class="mx-auto mt-12 flex max-w-6xl flex-col gap-20 px-2 lg:flex-row">
          <article class="prose-custom min-w-0 flex-1">${blocks}</article>
          <aside class="w-full lg:w-72">
            <div class="space-y-12">
              <section>
                <h4 class="mb-6 text-[0.7rem] uppercase tracking-[0.25em] text-on-surface/40">Source Metadata</h4>
                <div class="space-y-6">
                  <div class="flex flex-col gap-1">
                    <span class="text-xs text-on-surface/40">Source URL</span>
                    <a class="truncate text-sm font-medium text-primary hover:underline" href="${escapeHtml(first.url || job.source_value || "#")}">${escapeHtml(first.url || job.source_value || "")}</a>
                  </div>
                  <div class="flex flex-col gap-1">
                    <span class="text-xs text-on-surface/40">Duration</span>
                    <span class="text-sm font-medium text-on-surface">${job.duration_minutes ? formatMinutes(job.duration_minutes) : "—"}</span>
                  </div>
                  <div class="flex flex-col gap-1">
                    <span class="text-xs text-on-surface/40">Word Count</span>
                    <span class="text-sm font-medium text-on-surface">${(job.word_count || 0).toLocaleString()} words</span>
                  </div>
                </div>
              </section>
              <section>
                <h4 class="mb-6 text-[0.7rem] uppercase tracking-[0.25em] text-on-surface/40">Analysis Details</h4>
                <div class="space-y-6">
                  <div class="flex flex-col gap-1">
                    <span class="text-xs text-on-surface/40">Detected Language</span>
                    <div class="flex items-center gap-2">
                      <span class="material-symbols-outlined text-xs text-primary">language</span>
                      <span class="text-sm font-medium text-on-surface">${escapeHtml(languageLabel(job.language))}</span>
                    </div>
                  </div>
                  <div class="flex flex-col gap-1">
                    <span class="text-xs text-on-surface/40">Transcription Model</span>
                    <span class="w-max rounded bg-primary-fixed px-2 py-0.5 text-[0.65rem] font-bold uppercase tracking-[0.18em] text-on-primary-fixed-variant">${escapeHtml(job.model)}</span>
                  </div>
                  <div class="flex flex-col gap-1">
                    <span class="text-xs text-on-surface/40">Processing Time</span>
                    <div class="flex items-center gap-2">
                      <span class="material-symbols-outlined text-xs text-secondary">speed</span>
                      <span class="text-sm font-medium text-on-surface">${formatMinutes(job.duration_minutes || 0)}</span>
                    </div>
                  </div>
                </div>
              </section>
              <section class="rounded-xl bg-surface-container-low p-6">
                <h4 class="mb-4 text-[0.7rem] uppercase tracking-[0.25em] text-on-surface/40">Export Settings</h4>
                <p class="mb-6 text-[0.8rem] leading-relaxed text-on-surface/60">Adjust your preferred timestamp interval for future exports.</p>
                <div class="mb-2 flex items-center justify-between text-xs font-semibold">
                  <span>Frequency</span>
                  <span class="text-primary">Every 30s</span>
                </div>
                <div class="h-1.5 w-full overflow-hidden rounded-full bg-surface-container-highest">
                  <div class="h-full w-2/3 rounded-full bg-primary"></div>
                </div>
              </section>
            </div>
          </aside>
        </div>
      </div>
    `,
  );
}

function renderApiKeys() {
  const keys = state.bootstrap.api_keys;
  return appShell(
    "keys",
    "API Keys",
    `
      <div class="mx-auto max-w-6xl space-y-12">
        <section class="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div class="max-w-2xl">
            <h3 class="font-headline text-5xl tracking-tight">Authentication</h3>
            <p class="mt-4 text-lg leading-8 text-on-surface/62">Manage secret keys to authenticate your requests with the StoryToText API. Keep your keys secure and never share them publicly.</p>
          </div>
          <button data-action="toggle-key-composer" class="inline-flex items-center gap-2 rounded-md bg-gradient-to-r from-primary to-primary-container px-6 py-3 text-sm font-semibold text-on-primary shadow-editorial"><span class="material-symbols-outlined text-lg">add</span>Create new key</button>
        </section>

        ${
          state.keyComposerOpen
            ? `
              <form data-key-form class="rounded-[1.4rem] bg-white/82 p-6 shadow-editorial">
                <label class="block text-[11px] font-bold uppercase tracking-[0.22em] text-on-surface/38">Key name</label>
                <div class="mt-4 flex flex-col gap-4 md:flex-row">
                  <input name="name" class="flex-1 rounded-xl border-none bg-surface-container-low px-4 py-4 text-sm" placeholder="Production Main" />
                  <button class="rounded-md bg-primary px-6 py-4 text-sm font-semibold text-on-primary">Generate key</button>
                </div>
              </form>
            `
            : ""
        }

        ${
          state.lastCreatedSecret
            ? `
              <div class="rounded-[1.5rem] bg-primary-fixed p-7 shadow-editorial">
                <p class="text-[11px] font-bold uppercase tracking-[0.22em] text-primary/60">New API key created</p>
                <h4 class="mt-3 font-headline text-4xl">Copy this secret now</h4>
                <div class="mt-5 flex flex-col gap-4 md:flex-row md:items-center">
                  <code class="rounded-xl bg-white/70 px-4 py-3 text-sm text-on-surface">${escapeHtml(state.lastCreatedSecret)}</code>
                  <button data-copy-secret="${escapeHtml(state.lastCreatedSecret)}" class="rounded-md bg-primary px-5 py-3 text-sm font-semibold text-on-primary">Copy secret</button>
                </div>
              </div>
            `
            : ""
        }

        <section class="overflow-hidden rounded-[1.6rem] bg-white/82 shadow-editorial">
          <table class="min-w-full">
            <thead class="border-b border-outline-variant/16 text-left text-[11px] uppercase tracking-[0.22em] text-on-surface/38">
              <tr>
                <th class="px-6 py-5">Name</th>
                <th class="px-6 py-5">Secret key</th>
                <th class="px-6 py-5">Last used</th>
                <th class="px-6 py-5">Created</th>
                <th class="px-6 py-5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              ${
                keys.length
                  ? keys
                      .map(
                        (key) => `
                          <tr class="border-t border-outline-variant/12">
                            <td class="px-6 py-5 font-medium">${escapeHtml(key.name)}</td>
                            <td class="px-6 py-5"><code class="rounded bg-surface-variant/40 px-2 py-1 text-sm text-on-surface/65">${escapeHtml(key.masked)}</code></td>
                            <td class="px-6 py-5 text-sm text-on-surface/45">${key.last_used_at ? relativeTime(key.last_used_at) : "Never"}</td>
                            <td class="px-6 py-5 text-sm text-on-surface/45">${formatDateTime(key.created_at)}</td>
                            <td class="px-6 py-5 text-right">
                              <div class="flex justify-end gap-4">
                                <button data-copy-secret="${escapeHtml(key.masked)}" class="inline-flex items-center gap-1 text-sm font-medium text-on-surface/60 transition-colors hover:text-primary"><span class="material-symbols-outlined text-base">content_copy</span>Copy</button>
                                <button data-delete-key="${key.id}" class="inline-flex items-center gap-1 text-sm font-semibold text-error"><span class="material-symbols-outlined text-base">delete</span>Revoke</button>
                              </div>
                            </td>
                          </tr>
                        `,
                      )
                      .join("")
                  : `<tr><td colspan="5" class="px-6 py-12 text-center text-sm text-on-surface/55">No API keys yet. Create one to unlock REST access.</td></tr>`
              }
            </tbody>
          </table>
        </section>

        <section class="grid gap-6 lg:grid-cols-[1fr_0.44fr]">
          <div class="rounded-[1.6rem] bg-white/82 p-8 shadow-editorial">
            <div class="flex items-center gap-3">
              <div class="grid h-11 w-11 place-items-center rounded-full bg-primary text-on-primary"><span class="material-symbols-outlined">verified_user</span></div>
              <h4 class="font-headline text-3xl">Security Protocol</h4>
            </div>
            <p class="mt-6 max-w-3xl text-sm leading-8 text-on-surface/62">For your protection, we employ a <strong>copy-once security pattern</strong>. Your secret API keys are only visible at the moment of creation. If you lose a key, you must revoke it and generate a new one.</p>
            <div class="mt-6 space-y-3">
              <div class="flex items-center gap-3 text-sm text-on-surface/62"><span class="material-symbols-outlined text-base text-primary">check_circle</span>Rotating keys every 90 days is recommended.</div>
              <div class="flex items-center gap-3 text-sm text-on-surface/62"><span class="material-symbols-outlined text-base text-primary">check_circle</span>Never commit keys to version control (GitHub, GitLab).</div>
            </div>
          </div>
          <div class="rounded-[1.6rem] bg-primary p-8 text-on-primary shadow-editorial">
            <div class="flex items-center justify-between">
              <p class="text-[11px] uppercase tracking-[0.22em] text-primary-fixed">Usage Quota</p>
              <span class="rounded-full bg-primary-fixed px-3 py-1 text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Tier: ${escapeHtml(state.bootstrap.billing.plan)}</span>
            </div>
            <div class="mt-6 space-y-6">
              <div>
                <p class="text-sm text-white/72">API Requests</p>
                <p class="mt-2 font-headline text-4xl">${state.bootstrap.health.api_request_count.toLocaleString()} <span class="text-lg text-white/50">/ 50,000</span></p>
              </div>
              <div>
                <p class="text-sm text-white/72">Transcription Hours</p>
                <p class="mt-2 font-headline text-4xl">${(state.bootstrap.billing.api_minutes / 60).toFixed(1)} <span class="text-lg text-white/50">/ 100</span></p>
              </div>
            </div>
            <button data-nav="/billing" class="mt-6 flex items-center gap-2 text-sm font-medium text-primary-fixed transition-colors hover:text-white">Manage Limits <span class="material-symbols-outlined text-sm">arrow_forward</span></button>
          </div>
        </section>

        <section class="grid gap-6 md:grid-cols-3">
          <div class="rounded-[1.6rem] bg-white/82 p-8 shadow-editorial">
            <span class="material-symbols-outlined mb-4 text-3xl text-primary">menu_book</span>
            <h4 class="font-headline text-2xl font-bold">SDK Reference</h4>
            <p class="mt-3 text-sm leading-7 text-on-surface/55">Official libraries for Python, Node.js, and Go to speed up your integration.</p>
          </div>
          <div class="rounded-[1.6rem] bg-white/82 p-8 shadow-editorial">
            <span class="material-symbols-outlined mb-4 text-3xl text-primary">webhook</span>
            <h4 class="font-headline text-2xl font-bold">Webhooks</h4>
            <p class="mt-3 text-sm leading-7 text-on-surface/55">Configure endpoints to receive real-time notifications for completed tasks.</p>
          </div>
          <div class="rounded-[1.6rem] bg-white/82 p-8 shadow-editorial">
            <span class="material-symbols-outlined mb-4 text-3xl text-primary">monitoring</span>
            <h4 class="font-headline text-2xl font-bold">Service Status</h4>
            <p class="mt-3 text-sm leading-7 text-on-surface/55">Check the current health and performance metrics of our global API nodes.</p>
          </div>
        </section>
      </div>
    `,
  );
}

function renderBilling() {
  const billing = state.bootstrap.billing;
  const invoices = [
    { date: new Date(), amount: `$${billing.price_monthly}.00`, invoice_id: `STT-2024-009`, status: "paid" },
    { date: new Date(Date.now() - 86400000 * 30), amount: `$${billing.price_monthly}.00`, invoice_id: `STT-2024-008`, status: "paid" },
    { date: new Date(Date.now() - 86400000 * 60), amount: "$29.00", invoice_id: `STT-2024-007`, status: "paid" },
  ];

  return appShell(
    "billing",
    "Billing & Subscription",
    `
      <div class="mx-auto max-w-6xl space-y-12">
        <p class="text-on-surface/55">Manage your plan, usage, and financial records.</p>

        <div class="grid gap-8 lg:grid-cols-[1fr_0.48fr]">
          <section class="space-y-8">
            <div class="grid gap-8 md:grid-cols-[1fr_auto]">
              <div class="rounded-[1.6rem] bg-white/82 p-8 shadow-editorial">
                <p class="text-[11px] uppercase tracking-[0.22em] text-primary/55">Current plan</p>
                <span class="mt-4 inline-flex rounded-full bg-primary-fixed px-3 py-1 text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Professional</span>
                <h3 class="mt-4 font-headline text-5xl">Pro Plan</h3>
                <div class="mt-3 flex items-baseline gap-2">
                  <span class="text-3xl font-semibold text-primary">$${billing.price_monthly}</span>
                  <span class="text-sm text-on-surface/45">/ month</span>
                </div>
                <div class="mt-4 flex items-center gap-2 text-sm text-on-surface/55">
                  <span class="material-symbols-outlined text-base">calendar_today</span>
                  Next renewal: ${formatDateTime(billing.next_renewal)}
                </div>
                <div class="mt-6 flex flex-wrap gap-3">
                  <button data-action="plan-toast" class="rounded-md bg-primary px-6 py-3 text-sm font-semibold text-on-primary">Manage Subscription</button>
                  <button data-action="plan-toast" class="rounded-md bg-surface-container-high px-6 py-3 text-sm font-semibold text-on-surface">Switch to Yearly</button>
                </div>
              </div>
            </div>

            <div class="rounded-[1.6rem] bg-white/82 p-8 shadow-editorial">
              <div class="flex items-start justify-between">
                <div>
                  <p class="text-[11px] uppercase tracking-[0.22em] text-on-surface/35">Usage overview</p>
                  <h4 class="mt-3 font-headline text-3xl italic">Credits & Minutes Used</h4>
                  <p class="mt-1 text-sm text-on-surface/45">Total combined processing time</p>
                </div>
                <div class="flex items-baseline gap-1 text-right">
                  <span class="text-3xl font-semibold">${billing.minutes_used}</span>
                  <span class="text-sm text-on-surface/45">/ ${billing.minutes_limit} min</span>
                </div>
              </div>
              <div class="mt-6 h-3 rounded-full bg-surface-container-high">
                <div class="h-full rounded-full bg-primary" style="width:${Math.min(billing.usage_pct, 100)}%"></div>
              </div>
              <div class="mt-6 grid gap-4 md:grid-cols-2">
                <div class="flex items-center justify-between text-xs font-bold uppercase tracking-[0.18em]"><span>Web Platform</span><span>${billing.web_minutes} min</span></div>
                <div class="flex items-center justify-between text-xs font-bold uppercase tracking-[0.18em]"><span>API Integration</span><span>${billing.api_minutes} min</span></div>
              </div>
              <p class="mt-4 text-right text-xs text-on-surface/35">Cycle ends in ${billing.cycle_days_left} days</p>
            </div>
          </section>

          <section class="space-y-8">
            <div class="rounded-[1.6rem] bg-white/82 p-8 shadow-editorial">
              <h4 class="font-headline text-3xl">Payment Methods</h4>
              <div class="mt-6 flex items-center gap-4 rounded-2xl border border-outline-variant/18 bg-surface-container-low p-5">
                <div class="grid h-10 w-14 place-items-center rounded bg-surface-container-highest text-xs font-bold text-on-surface/60">VISA</div>
                <div>
                  <p class="font-medium">Visa ending in 4242</p>
                  <p class="mt-1 text-sm text-on-surface/45">Expires 08/26 &middot; Primary</p>
                </div>
              </div>
              <button data-action="plan-toast" class="mt-5 flex items-center gap-2 text-sm font-medium text-on-surface/60 transition-colors hover:text-primary"><span class="material-symbols-outlined text-lg">add</span>Add Payment Method</button>
            </div>
            <div class="rounded-[1.6rem] bg-primary p-8 text-on-primary shadow-editorial">
              <h4 class="font-headline text-4xl leading-tight italic">Preserving Every Spoken Word.</h4>
              <p class="mt-4 text-sm leading-8 text-white/78">Our archival-grade transcription engine ensures your stories last a lifetime. Upgrade for priority processing and unlimited API access.</p>
              <button data-nav="/docs" class="mt-6 flex items-center gap-2 rounded-md bg-white px-5 py-3 text-sm font-semibold text-primary">Explore API Docs <span class="material-symbols-outlined text-sm">arrow_forward</span></button>
            </div>
          </section>
        </div>

        <section class="rounded-[1.6rem] bg-white/82 p-8 shadow-editorial">
          <p class="text-[11px] font-bold uppercase tracking-[0.22em] text-on-surface/35">Billing history</p>
          <div class="mt-6 overflow-hidden">
            <table class="min-w-full text-left">
              <thead class="text-[0.65rem] font-bold uppercase tracking-[0.22em] text-on-surface/40">
                <tr>
                  <th class="pb-4 pr-6">Date</th>
                  <th class="pb-4 pr-6">Amount</th>
                  <th class="pb-4 pr-6">Invoice ID</th>
                  <th class="pb-4 pr-6">Status</th>
                  <th class="pb-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-outline-variant/10">
                ${invoices
                  .map(
                    (inv) => `
                      <tr class="table-hover-row">
                        <td class="py-5 pr-6 text-sm">${formatDateTime(inv.date)}</td>
                        <td class="py-5 pr-6 text-sm font-semibold">${inv.amount}</td>
                        <td class="py-5 pr-6 text-sm text-on-surface/55">${inv.invoice_id}</td>
                        <td class="py-5 pr-6"><span class="inline-flex rounded-full bg-primary-fixed px-3 py-1 text-[10px] font-bold uppercase tracking-[0.18em] text-on-primary-fixed-variant">Paid</span></td>
                        <td class="py-5 text-right"><button data-action="invoice-toast" class="inline-flex items-center gap-1 text-sm font-semibold text-error"><span class="material-symbols-outlined text-base">download</span>Download PDF</button></td>
                      </tr>
                    `,
                  )
                  .join("")}
              </tbody>
            </table>
          </div>
          <div class="mt-6 text-center">
            <button data-action="invoice-toast" class="text-xs font-bold uppercase tracking-[0.22em] text-on-surface/40 transition-colors hover:text-primary">View Full History</button>
          </div>
        </section>

        <footer class="border-t border-outline-variant/10 pt-8 text-center text-xs text-on-surface/35">
          <p>&copy; 2024 StoryToText. All rights reserved. Built for the modern archivist.</p>
          <div class="mt-3 flex justify-center gap-6">
            <button class="hover:text-primary">Terms of Service</button>
            <button class="hover:text-primary">Privacy Policy</button>
            <button class="hover:text-primary">Status</button>
          </div>
        </footer>
      </div>
    `,
  );
}

function renderDocs() {
  const sampleKey = state.bootstrap.api_keys[0]?.masked || "st_live_••••••••0000";
  const curlSample = `# Create a transcription request\ncurl --request POST \\\n  --url http://localhost:7860/api/v1/transcriptions \\\n  --header ‘Authorization: Bearer ${sampleKey}’ \\\n  --header ‘Content-Type: application/json’ \\\n  --data ‘{\n    "mode": "single_url",\n    "source_value": "https://youtube.com/watch?v=...",\n    "language": "en",\n    "detect_speakers": true\n  }’`;
  const pythonExample = `import requests\n\nAPI_KEY = "${sampleKey}"\nBASE    = "http://localhost:7860/api/v1"\n\n# Create a transcription job\nres = requests.post(\n    f"{BASE}/transcriptions",\n    headers={"Authorization": f"Bearer {API_KEY}"},\n    json={\n        "mode": "single_url",\n        "source_value": "https://youtube.com/watch?v=...",\n        "language": "en"\n    }\n)\njob = res.json()\nprint(f"Job ID: {job[‘id’]}")`;
  return appShell(
    "docs",
    "Documentation",
    `
      <div class="mx-auto flex max-w-6xl gap-16">
        <aside class="hidden w-56 shrink-0 lg:block">
          <nav class="sticky top-28 space-y-8">
            <div>
              <h4 class="mb-4 text-[0.65rem] uppercase tracking-[0.2em] text-outline">Guides</h4>
              <ul class="space-y-3 text-sm">
                <li><button data-scroll-target="docs-quickstart" class="font-semibold text-primary">Quickstart</button></li>
                <li><button data-scroll-target="docs-auth" class="text-on-surface/70 transition-colors hover:text-primary">Authentication</button></li>
                <li><button data-scroll-target="docs-endpoints" class="text-on-surface/70 transition-colors hover:text-primary">API Endpoints</button></li>
                <li><button data-scroll-target="docs-webhooks" class="text-on-surface/70 transition-colors hover:text-primary">Webhooks</button></li>
              </ul>
            </div>
            <div>
              <h4 class="mb-4 text-[0.65rem] uppercase tracking-[0.2em] text-outline">Integrations</h4>
              <ul class="space-y-3 text-sm">
                <li><button data-scroll-target="docs-agent" class="text-on-surface/70 transition-colors hover:text-primary">AI Agent MCP</button></li>
                <li><button class="text-on-surface/70 transition-colors hover:text-primary">Zapier &amp; Make</button></li>
                <li><button class="text-on-surface/70 transition-colors hover:text-primary">Client SDKs</button></li>
              </ul>
            </div>
          </nav>
        </aside>

        <article class="min-w-0 max-w-4xl flex-1 space-y-24">
          <section id="docs-quickstart" class="scroll-mt-28">
            <div class="mb-10">
              <span class="text-[0.7rem] font-bold uppercase tracking-[0.3em] text-primary">The Archivist’s Toolkit</span>
              <h1 class="mt-4 mb-6 font-headline text-5xl leading-tight tracking-tight">Build the future of digital memory.</h1>
              <p class="max-w-2xl text-lg leading-relaxed text-on-surface/70">Integrate our state-of-the-art transcription engine into your applications. From batch processing journals to real-time AI memory, StoryToText provides the high-fidelity foundation your content deserves.</p>
            </div>
            <div class="mt-12 grid grid-cols-2 gap-8">
              <div class="rounded-lg bg-surface-container-low p-8">
                <h3 class="mb-3 font-headline text-xl italic">How it works</h3>
                <p class="text-sm leading-relaxed text-on-surface/70">Our API follows RESTful principles. Upload audio, wait for processing, and receive deeply structured text including speaker diarization and sentiment layers.</p>
              </div>
              <div class="relative overflow-hidden rounded-lg bg-[radial-gradient(circle_at_top_right,rgba(218,193,184,0.35),transparent_45%),linear-gradient(135deg,rgba(234,232,227,0.8),rgba(245,243,238,1))]">
                <div class="flex h-full items-center justify-center opacity-30">
                  <span class="material-symbols-outlined" style="font-size:5rem;font-variation-settings:’FILL’ 0,’wght’ 100">laptop_mac</span>
                </div>
              </div>
            </div>
          </section>

          <section id="docs-auth" class="scroll-mt-28">
            <div class="mb-8 flex items-baseline gap-4">
              <h2 class="font-headline text-3xl">Authentication</h2>
              <div class="h-px flex-1 bg-outline-variant/30"></div>
            </div>
            <p class="mb-6 text-sm leading-relaxed text-on-surface/70">Authenticating with the StoryToText API is done via a Bearer token in the Authorization header. You can generate your API keys in the dashboard. Keep these secure and do not share them in client-side code.</p>
            <div class="overflow-x-auto rounded-md bg-on-surface p-6 font-mono text-xs leading-relaxed text-surface shadow-xl">
              <div class="mb-4 flex items-center justify-between text-[10px] uppercase tracking-[0.2em] text-on-surface-variant/40">
                <span>Shell / Request</span>
                <button class="transition-colors hover:text-primary-fixed">Copy</button>
              </div>
              <pre><code><span class="text-tertiary-fixed">curl</span> -X GET http://localhost:7860/api/v1/me \\
  -H <span class="text-primary-fixed">"Authorization: Bearer ${escapeHtml(sampleKey)}"</span> \\
  -H <span class="text-primary-fixed">"Content-Type: application/json"</span></code></pre>
            </div>
          </section>

          <section id="docs-endpoints" class="scroll-mt-28">
            <h2 class="mb-8 font-headline text-3xl">Transcription Endpoints</h2>
            <div class="overflow-hidden rounded-md bg-surface-container-lowest ring-1 ring-outline-variant/20">
              <table class="w-full text-left">
                <thead>
                  <tr class="bg-surface-container-low/50">
                    <th class="px-6 py-4 text-[0.65rem] font-bold uppercase tracking-[0.2em] text-outline">Method</th>
                    <th class="px-6 py-4 text-[0.65rem] font-bold uppercase tracking-[0.2em] text-outline">Path</th>
                    <th class="px-6 py-4 text-[0.65rem] font-bold uppercase tracking-[0.2em] text-outline">Description</th>
                  </tr>
                </thead>
                <tbody class="text-sm">
                  <tr class="border-t border-outline-variant/10">
                    <td class="px-6 py-4"><span class="rounded bg-tertiary-container px-2 py-0.5 text-[10px] font-bold text-white">POST</span></td>
                    <td class="px-6 py-4 font-mono text-xs">/v1/transcriptions</td>
                    <td class="px-6 py-4 text-on-surface/60">Create a new transcription job from a URL or file upload.</td>
                  </tr>
                  <tr class="border-t border-outline-variant/10">
                    <td class="px-6 py-4"><span class="rounded bg-secondary px-2 py-0.5 text-[10px] font-bold text-white">GET</span></td>
                    <td class="px-6 py-4 font-mono text-xs">/v1/jobs/{id}</td>
                    <td class="px-6 py-4 text-on-surface/60">Retrieve the status and results of a specific job.</td>
                  </tr>
                  <tr class="border-t border-outline-variant/10">
                    <td class="px-6 py-4"><span class="rounded bg-secondary px-2 py-0.5 text-[10px] font-bold text-white">GET</span></td>
                    <td class="px-6 py-4 font-mono text-xs">/v1/history</td>
                    <td class="px-6 py-4 text-on-surface/60">List all transcription jobs for the current account.</td>
                  </tr>
                  <tr class="border-t border-outline-variant/10">
                    <td class="px-6 py-4"><span class="rounded bg-error px-2 py-0.5 text-[10px] font-bold text-white">DELETE</span></td>
                    <td class="px-6 py-4 font-mono text-xs">/v1/jobs/{id}</td>
                    <td class="px-6 py-4 text-on-surface/60">Permanently delete a record and its associated data.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section id="docs-webhooks" class="scroll-mt-28 space-y-6">
            <div class="flex items-center gap-6 border-b border-outline-variant/20">
              <button class="border-b-2 border-primary pb-3 text-sm font-bold text-primary">cURL</button>
              <button class="pb-3 text-sm font-medium text-on-surface/40 transition-colors hover:text-on-surface">JavaScript</button>
              <button class="pb-3 text-sm font-medium text-on-surface/40 transition-colors hover:text-on-surface">Python</button>
              <button class="pb-3 text-sm font-medium text-on-surface/40 transition-colors hover:text-on-surface">Ruby</button>
            </div>
            <div class="overflow-x-auto rounded-md bg-on-surface p-8 font-mono text-[13px] leading-relaxed text-surface shadow-lg">
              <pre><code>${escapeHtml(curlSample)}</code></pre>
            </div>
          </section>

          <section id="docs-agent" class="scroll-mt-28 pb-20">
            <h2 class="mb-8 font-headline text-3xl">AI Agent Integration</h2>
            <div class="grid grid-cols-3 gap-6">
              <div class="relative col-span-2 overflow-hidden rounded-xl bg-primary-fixed p-10">
                <div class="relative z-10">
                  <h3 class="mb-4 font-headline text-2xl text-on-primary-fixed">The MCP Wrapper</h3>
                  <p class="max-w-md text-sm leading-relaxed text-on-primary-fixed-variant">Expose StoryToText to Claude, Codex, or GPT-4 through our Model Context Protocol wrapper. Allow your agents to "hear" audio files directly within their workspace.</p>
                  <button data-nav="/api-keys" class="mt-8 rounded bg-on-primary-fixed px-6 py-2.5 text-xs font-bold text-white transition-opacity hover:opacity-90">Get the SDK</button>
                </div>
                <span class="material-symbols-outlined absolute -bottom-10 -right-10 text-[12rem] text-on-primary-fixed opacity-5">memory</span>
              </div>
              <div class="flex flex-col justify-center rounded-xl bg-surface-container-highest p-8">
                <span class="material-symbols-outlined mb-4 text-4xl text-primary">hub</span>
                <h4 class="mb-2 text-sm font-bold">Native Webhooks</h4>
                <p class="text-xs leading-relaxed text-on-surface/60">Push final transcriptions directly into your Vector DB for RAG workflows.</p>
              </div>
            </div>
            <div class="mt-12 rounded-lg border border-outline-variant/10 bg-surface-container-low p-12">
              <div class="flex flex-col items-center gap-12 md:flex-row">
                <div class="flex-1">
                  <h3 class="mb-4 font-headline text-2xl italic">"The Contextual Bridge"</h3>
                  <p class="mb-6 text-sm leading-relaxed text-on-surface/70">In modern AI development, the bottleneck isn’t the model—it’s the data quality. StoryToText provides timestamped, diarized JSON that models like Claude can parse natively to understand the nuances of human interaction.</p>
                  <ul class="space-y-4">
                    <li class="flex items-center gap-3 text-xs font-bold tracking-tight"><span class="material-symbols-outlined text-primary">check_circle</span>AUTOMATIC SPEAKER IDENTIFICATION</li>
                    <li class="flex items-center gap-3 text-xs font-bold tracking-tight"><span class="material-symbols-outlined text-primary">check_circle</span>SENTIMENT SCORE PER UTTERANCE</li>
                    <li class="flex items-center gap-3 text-xs font-bold tracking-tight"><span class="material-symbols-outlined text-primary">check_circle</span>SUB-SECOND LATENCY FOR STREAMING</li>
                  </ul>
                </div>
                <div class="aspect-square w-full overflow-hidden rounded-full shadow-2xl ring-8 ring-surface-container md:w-1/3">
                  <div class="flex h-full w-full items-center justify-center bg-[radial-gradient(circle_at_30%_30%,rgba(0,114,128,0.6),rgba(0,88,99,0.8))]">
                    <span class="material-symbols-outlined text-6xl text-white/30">memory</span>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </article>

        <aside class="hidden w-48 shrink-0 lg:block">
          <div class="sticky top-28">
            <h4 class="mb-6 text-[10px] font-bold uppercase tracking-[0.2em] text-outline">On this page</h4>
            <ul class="space-y-4 border-l border-outline-variant/20 pl-4 text-[11px] font-medium text-on-surface/50">
              <li><button data-scroll-target="docs-quickstart" class="transition-colors hover:text-primary">How it works</button></li>
              <li><button data-scroll-target="docs-auth" class="transition-colors hover:text-primary">Auth Header</button></li>
              <li><button data-scroll-target="docs-endpoints" class="transition-colors hover:text-primary">Endpoint Table</button></li>
              <li><button data-scroll-target="docs-agent" class="transition-colors hover:text-primary">AI &amp; MCP</button></li>
            </ul>
            <div class="mt-16 rounded-lg border border-outline-variant/10 bg-surface-container-low p-4">
              <p class="mb-3 text-[10px] italic leading-relaxed text-on-surface/40">Need human help?</p>
              <button data-action="support-toast" class="flex items-center gap-2 text-[11px] font-bold text-primary">
                Talk to an Engineer
                <span class="material-symbols-outlined text-xs">arrow_forward</span>
              </button>
            </div>
          </div>
        </aside>
      </div>
    `,
  );
}

function renderSettings() {
  const user = state.bootstrap.user;
  const settings = state.bootstrap.settings;
  return appShell(
    "settings",
    "Settings",
    `
      <div class="mx-auto max-w-6xl">
        <div class="grid gap-12 lg:grid-cols-[220px_1fr]">
          <aside class="rounded-[1.5rem] bg-white/82 p-6 shadow-editorial lg:sticky lg:top-28 h-fit">
            <h3 class="font-headline text-3xl italic">Settings</h3>
            <p class="mt-2 text-sm text-on-surface/55">Manage your account and preferences.</p>
            <div class="mt-8 space-y-2 text-sm">
              <button data-scroll-target="settings-profile" class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-primary transition-colors hover:bg-surface-container-low"><span class="material-symbols-outlined text-base">person</span>Profile</button>
              <button data-scroll-target="settings-transcription" class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-on-surface/60 transition-colors hover:bg-surface-container-low"><span class="material-symbols-outlined text-base">tune</span>Transcription</button>
              <button data-scroll-target="settings-security" class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-on-surface/60 transition-colors hover:bg-surface-container-low"><span class="material-symbols-outlined text-base">shield</span>Security</button>
            </div>
            <div class="mt-10 rounded-2xl bg-primary-fixed/35 p-4 text-sm">
              <p class="text-[10px] font-bold uppercase tracking-[0.18em] text-primary/55">Plan: ${escapeHtml(state.bootstrap.billing.plan)}</p>
              <p class="mt-2 text-on-surface/62">You have ${state.bootstrap.billing.minutes_limit - state.bootstrap.billing.minutes_used} transcription minutes remaining this cycle.</p>
            </div>
          </aside>
          <form data-settings-form class="space-y-12">
            <section id="settings-profile" class="rounded-[1.6rem] bg-white/82 p-8 shadow-editorial">
              <div class="flex items-start justify-between">
                <div>
                  <h3 class="font-headline text-4xl italic">Profile Settings</h3>
                  <p class="mt-3 max-w-2xl text-sm leading-7 text-on-surface/62">Your public identity within the StoryToText workspace. This information shapes account-level notifications and developer ownership.</p>
                </div>
                <div class="flex flex-col items-center gap-3">
                  <div class="grid h-16 w-16 place-items-center rounded-full bg-primary text-2xl font-bold text-on-primary">${(user.full_name || "U").charAt(0)}</div>
                  <button type="button" data-action="support-toast" class="text-xs font-medium text-primary transition-colors hover:underline">Change Photo</button>
                </div>
              </div>
              <div class="mt-8 grid gap-6 md:grid-cols-2">
                <div>
                  <label for="settings-full-name" class="text-[11px] font-bold uppercase tracking-[0.22em] text-on-surface/38">Full name</label>
                  <input id="settings-full-name" name="full_name" value="${escapeHtml(user.full_name || "")}" class="mt-3 w-full rounded-xl border-none bg-surface-container-low px-4 py-4 text-sm" />
                </div>
                <div>
                  <label for="settings-email" class="text-[11px] font-bold uppercase tracking-[0.22em] text-on-surface/38">Email address</label>
                  <input id="settings-email" name="email" value="${escapeHtml(user.email || "")}" class="mt-3 w-full rounded-xl border-none bg-surface-container-low px-4 py-4 text-sm" />
                </div>
              </div>
              <div class="mt-6">
                <label for="settings-bio" class="text-[11px] font-bold uppercase tracking-[0.22em] text-on-surface/38">Bio</label>
                <textarea id="settings-bio" name="bio" rows="4" class="mt-3 w-full rounded-xl border-none bg-surface-container-low px-4 py-4 text-sm">${escapeHtml(user.bio || "")}</textarea>
              </div>
              <div class="mt-6">
                <label for="settings-timezone" class="text-[11px] font-bold uppercase tracking-[0.22em] text-on-surface/38">Timezone</label>
                <input id="settings-timezone" name="timezone" value="${escapeHtml(user.timezone || "Europe/Istanbul")}" class="mt-3 w-full rounded-xl border-none bg-surface-container-low px-4 py-4 text-sm" />
              </div>
            </section>

            <section id="settings-transcription" class="rounded-[1.6rem] bg-white/82 p-8 shadow-editorial">
              <h3 class="font-headline text-4xl italic">Transcription Preferences</h3>
              <div class="mt-8 grid gap-6 md:grid-cols-2">
                <div>
                  <label for="settings-default-language" class="text-[11px] font-bold uppercase tracking-[0.22em] text-on-surface/38">Default language</label>
                  <div class="mt-3">${formSelect("default_language", settings.default_language, LANGUAGE_OPTIONS).replace('<select ', '<select id="settings-default-language" ')}</div>
                </div>
                <div>
                  <label for="settings-default-model" class="text-[11px] font-bold uppercase tracking-[0.22em] text-on-surface/38">Default AI model</label>
                  <div class="mt-3">${formSelect("default_model", settings.default_model, MODEL_OPTIONS).replace('<select ', '<select id="settings-default-model" ')}</div>
                </div>
              </div>
              <div class="mt-8 space-y-4">
                <label class="flex items-center justify-between gap-4 rounded-2xl bg-surface-container-low px-5 py-4">
                  <div>
                    <p class="font-semibold text-on-surface">Auto-detect language</p>
                    <p class="mt-1 text-sm text-on-surface/55">Automatically detect the spoken language during transcription.</p>
                  </div>
                  <div class="relative">
                    <input name="auto_detect_language" type="checkbox" class="switch-input sr-only" />
                    <div class="switch" data-on="false"></div>
                  </div>
                </label>
                <label class="flex items-center justify-between gap-4 rounded-2xl bg-surface-container-low px-5 py-4">
                  <div>
                    <p class="font-semibold text-on-surface">Email me when jobs are complete</p>
                    <p class="mt-1 text-sm text-on-surface/55">Send me a direct path back to finished transcripts.</p>
                  </div>
                  <div class="relative">
                    <input name="email_on_complete" type="checkbox" class="switch-input sr-only" ${settings.email_on_complete ? "checked" : ""} />
                    <div class="switch" data-on="${settings.email_on_complete ? "true" : "false"}"></div>
                  </div>
                </label>
                <label class="flex items-center justify-between gap-4 rounded-2xl bg-surface-container-low px-5 py-4">
                  <div>
                    <p class="font-semibold text-on-surface">Enable speaker detection by default</p>
                    <p class="mt-1 text-sm text-on-surface/55">Persist speaker separation as the preferred processing behavior.</p>
                  </div>
                  <div class="relative">
                    <input name="speaker_detection" type="checkbox" class="switch-input sr-only" ${settings.speaker_detection ? "checked" : ""} />
                    <div class="switch" data-on="${settings.speaker_detection ? "true" : "false"}"></div>
                  </div>
                </label>
                <label class="flex items-center justify-between gap-4 rounded-2xl bg-surface-container-low px-5 py-4">
                  <div>
                    <p class="font-semibold text-on-surface">Receive product updates</p>
                    <p class="mt-1 text-sm text-on-surface/55">Stay informed about new archival features and editorial improvements.</p>
                  </div>
                  <div class="relative">
                    <input name="product_updates" type="checkbox" class="switch-input sr-only" ${settings.product_updates ? "checked" : ""} />
                    <div class="switch" data-on="${settings.product_updates ? "true" : "false"}"></div>
                  </div>
                </label>
              </div>
            </section>

            <section id="settings-security" class="rounded-[1.6rem] bg-white/82 p-8 shadow-editorial">
              <h3 class="font-headline text-4xl italic">Security</h3>
              <p class="mt-4 text-sm leading-7 text-on-surface/62">StoryToText keeps account-level secrets local to this workspace. Revoke API keys any time from the API Keys section.</p>
              <div class="mt-8 space-y-4">
                <div class="flex items-center justify-between rounded-2xl bg-surface-container-low px-5 py-4">
                  <div>
                    <p class="font-semibold text-on-surface">Two-Factor Authentication</p>
                    <p class="mt-1 text-sm text-on-surface/55">Add an extra layer of security to your account.</p>
                  </div>
                  <span class="rounded-full bg-surface-container-highest px-3 py-1 text-[10px] font-bold uppercase tracking-[0.18em] text-on-surface/55">Coming Soon</span>
                </div>
                <div class="flex items-center justify-between rounded-2xl bg-surface-container-low px-5 py-4">
                  <div>
                    <p class="font-semibold text-on-surface">Shielded Location</p>
                    <p class="mt-1 text-sm text-on-surface/55">The Real Cloud V2 &middot; Frankfurt, DE</p>
                  </div>
                  <span class="material-symbols-outlined text-primary">check_circle</span>
                </div>
              </div>
              <div class="mt-8 rounded-2xl border border-error/20 bg-error-container/40 p-6">
                <h4 class="font-headline text-3xl italic text-error">Danger Zone</h4>
                <p class="mt-3 text-sm leading-7 text-on-error-container">This local workspace keeps state on disk inside <code class="rounded bg-error-container px-1.5 py-0.5 text-xs">runtime_data/state.json</code>. Removing that file resets demo content, API keys, billing state, and archive history.</p>
                <button type="button" data-action="support-toast" class="mt-5 rounded-md border border-error/30 bg-error-container px-5 py-2.5 text-sm font-semibold text-on-error-container transition-colors hover:bg-error hover:text-on-error">Delete Workspace</button>
              </div>
            </section>

            <div class="flex justify-end">
              <button class="rounded-md bg-primary px-8 py-3 text-sm font-semibold text-on-primary shadow-editorial">Save changes</button>
            </div>
          </form>
        </div>
      </div>
    `,
  );
}

function formatChunkRange(timestamp) {
  if (!timestamp || timestamp.length !== 2) return "00:00 — 00:00";
  const format = (value) => {
    const total = Math.max(0, Math.floor(Number(value) || 0));
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const seconds = total % 60;
    return hours ? `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}` : `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  };
  return `${format(timestamp[0])} — ${format(timestamp[1])}`;
}

function languageLabel(value) {
  return LANGUAGE_OPTIONS.find(([code]) => code === value)?.[1] || value || "Auto-detect";
}

function resolveRoute(pathname) {
  if (pathname === "/pricing") return { page: "landing", section: "pricing" };
  if (pathname === "/resources") return { page: "landing", section: "resources" };
  if (pathname === "/onboarding/intent") return { page: "onboarding-intent" };
  if (pathname === "/onboarding/source") return { page: "onboarding-source" };
  if (pathname === "/onboarding/final") return { page: "onboarding-final" };
  if (pathname === "/dashboard") return { page: "dashboard" };
  if (pathname === "/new") return { page: "new" };
  if (pathname === "/history") return { page: "history" };
  if (pathname === "/api-keys") return { page: "keys" };
  if (pathname === "/billing") return { page: "billing" };
  if (pathname === "/docs") return { page: "docs" };
  if (pathname === "/settings") return { page: "settings" };
  if (pathname.startsWith("/jobs/")) return { page: "job", id: pathname.split("/")[2] };
  if (pathname.startsWith("/transcripts/")) return { page: "detail", id: pathname.split("/")[2] };
  return { page: "landing", section: "" };
}

function render() {
  window.clearInterval(state.pollHandle);
  const route = resolveRoute(window.location.pathname);
  let markup = "";

  if (!state.bootstrap) {
    app.innerHTML = `<div class="grid min-h-screen place-items-center"><div class="rounded-3xl bg-white/80 px-6 py-4 shadow-editorial">Loading StoryToText…</div></div>`;
    return;
  }

  switch (route.page) {
    case "onboarding-intent":
      markup = renderOnboardingIntent();
      break;
    case "onboarding-source":
      markup = renderOnboardingSource();
      break;
    case "onboarding-final":
      markup = renderOnboardingFinal();
      break;
    case "dashboard":
      markup = renderDashboard();
      break;
    case "new":
      markup = renderNewTranscription();
      break;
    case "history":
      markup = renderHistory();
      break;
    case "job":
      markup = renderJobProcessing(route.id);
      startJobPolling(route.id);
      break;
    case "detail":
      markup = renderTranscriptDetail(route.id);
      break;
    case "keys":
      markup = renderApiKeys();
      break;
    case "billing":
      markup = renderBilling();
      break;
    case "docs":
      markup = renderDocs();
      break;
    case "settings":
      markup = renderSettings();
      break;
    default:
      markup = renderLanding(route.section);
  }

  app.innerHTML = markup;
  syncHistorySearchInput();
  applyHistoryDomFilter();
}

function syncHistorySearchInput() {
  const input = document.getElementById("history-search");
  if (input) input.value = state.historyQuery;
}

async function startJobPolling(jobId) {
  const poll = async () => {
    try {
      const job = await apiGet(`/api/jobs/${jobId}`);
      state.bootstrap.jobs = state.bootstrap.jobs.map((item) => (item.id === jobId ? job : item));
      if (job.status === "completed" || job.status === "failed") {
        await refreshBootstrap();
        render();
        if (job.status === "completed") toast("Transcript is ready.");
        return;
      }
      render();
    } catch (error) {
      console.error(error);
    }
  };
  state.pollHandle = window.setInterval(poll, 3000);
}

document.addEventListener("click", async (event) => {
  const nav = event.target.closest("[data-nav]");
  if (nav) {
    event.preventDefault();
    navigate(nav.dataset.nav);
    return;
  }

  const scroller = event.target.closest("[data-scroll-target]");
  if (scroller) {
    const target = document.getElementById(scroller.dataset.scrollTarget);
    target?.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }

  const startFlow = event.target.closest("[data-action='start-flow']");
  if (startFlow) {
    navigate(state.bootstrap.onboarding.completed ? "/dashboard" : "/onboarding/intent");
    return;
  }

  const onboardingIntent = event.target.closest("[data-onboarding-intent]");
  if (onboardingIntent) {
    state.onboardingDraft.intent = onboardingIntent.dataset.onboardingIntent;
    render();
    return;
  }

  const onboardingSource = event.target.closest("[data-onboarding-source]");
  if (onboardingSource) {
    state.onboardingDraft.source_preference = onboardingSource.dataset.onboardingSource;
    render();
    return;
  }

  const transcriptionTab = event.target.closest("[data-transcription-tab]");
  if (transcriptionTab) {
    state.form.mode = transcriptionTab.dataset.transcriptionTab;
    state.form.platform_hint = state.form.mode === "upload_files" ? "upload" : state.form.platform_hint || "youtube";
    render();
    return;
  }

  const retry = event.target.closest("[data-retry-job]");
  if (retry) {
    try {
      const job = await apiPost(`/api/jobs/${retry.dataset.retryJob}/retry`, {});
      await refreshBootstrap();
      navigate(`/jobs/${job.id}`);
      toast("Retry queued.");
    } catch (error) {
      toast(error.message);
    }
    return;
  }

  const copyTranscript = event.target.closest("[data-copy-job]");
  if (copyTranscript) {
    const job = state.bootstrap.jobs.find((item) => item.id === copyTranscript.dataset.copyJob);
    const text = (job?.results || []).map((result) => result.transcription || "").join("\n\n");
    await navigator.clipboard.writeText(text);
    toast("Transcript copied.");
    return;
  }

  const copySecret = event.target.closest("[data-copy-secret]");
  if (copySecret) {
    await navigator.clipboard.writeText(copySecret.dataset.copySecret);
    toast("Secret copied.");
    return;
  }

  const toggleKeyComposer = event.target.closest("[data-action='toggle-key-composer']");
  if (toggleKeyComposer) {
    state.keyComposerOpen = !state.keyComposerOpen;
    render();
    return;
  }

  const deleteKey = event.target.closest("[data-delete-key]");
  if (deleteKey) {
    if (!window.confirm("Revoke this API key?")) return;
    try {
      await apiDelete(`/api/keys/${deleteKey.dataset.deleteKey}`);
      await refreshBootstrap();
      render();
      toast("API key revoked.");
    } catch (error) {
      toast(error.message);
    }
    return;
  }

  const historyPage = event.target.closest("[data-history-page]");
  if (historyPage) {
    state.historyPage = Number(historyPage.dataset.historyPage);
    render();
    return;
  }

  const historyFilter = event.target.closest("[data-history-filter]");
  if (historyFilter) {
    state.historyFilter = historyFilter.dataset.historyFilter;
    state.historyPage = 1;
    render();
    return;
  }

  if (event.target.closest("[data-action='plan-toast']")) toast("Subscription controls are demo-ready in this local workspace.");
  if (event.target.closest("[data-action='support-toast']")) toast("Support flow is not connected yet, but the workspace state is fully local.");
  if (event.target.closest("[data-action='notifications-toast']")) toast("No new notifications.");
  if (event.target.closest("[data-action='invoice-toast']")) toast("Invoice export is visual-only in this local build.");
});

document.addEventListener("input", (event) => {
  const target = event.target;
  if (target.id === "history-search") {
    state.historyQuery = target.value;
    applyHistoryDomFilter();
  }
});

document.addEventListener("submit", async (event) => {
  const form = event.target;

  if (form.matches("[data-onboarding-intent-form]")) {
    event.preventDefault();
    try {
      await apiPost("/api/onboarding", { intent: state.onboardingDraft.intent });
      await refreshBootstrap();
      navigate("/onboarding/source");
    } catch (error) {
      toast(error.message);
    }
    return;
  }

  if (form.matches("[data-onboarding-source-form]")) {
    event.preventDefault();
    try {
      await apiPost("/api/onboarding", { source_preference: state.onboardingDraft.source_preference });
      await refreshBootstrap();
      navigate("/onboarding/final");
    } catch (error) {
      toast(error.message);
    }
    return;
  }

  if (form.matches("[data-onboarding-final-form]")) {
    event.preventDefault();
    const fd = new FormData(form);
    try {
      await apiPost("/api/settings", {
        default_language: fd.get("default_language"),
        default_language_label: languageLabel(fd.get("default_language")),
        email_on_complete: fd.get("email_on_complete") === "on",
        product_updates: fd.get("product_updates") === "on",
      });
      await apiPost("/api/onboarding", { completed: true });
      await refreshBootstrap();
      navigate("/dashboard");
      toast("Workspace configured.");
    } catch (error) {
      toast(error.message);
    }
    return;
  }

  if (form.matches("[data-new-job-form]")) {
    event.preventDefault();
    const fd = new FormData(form);
    const mode = state.form.mode;
    try {
      let job;
      if (mode === "upload_files") {
        const body = new FormData();
        body.append("mode", mode);
        body.append("platform_hint", "upload");
        body.append("language", fd.get("language"));
        body.append("model", fd.get("model"));
        body.append("speaker_detection", fd.get("speaker_detection") === "on" ? "true" : "false");
        body.append("title", "Uploaded media archive");
        const files = form.querySelector("input[type='file']").files;
        for (const file of files) body.append("media", file);
        job = await apiPost("/api/jobs", body, true);
      } else {
        job = await apiPost("/api/jobs", {
          mode,
          source_value: fd.get("source_value"),
          platform_hint: mode === "profile_batch" ? fd.get("platform_hint") : undefined,
          language: fd.get("language"),
          model: fd.get("model"),
          speaker_detection: fd.get("speaker_detection") === "on",
        });
      }
      await refreshBootstrap();
      navigate(`/jobs/${job.id}`);
    } catch (error) {
      toast(error.message);
    }
    return;
  }

  if (form.matches("[data-key-form]")) {
    event.preventDefault();
    const fd = new FormData(form);
    try {
      const created = await apiPost("/api/keys", { name: fd.get("name") });
      state.lastCreatedSecret = created.secret;
      state.keyComposerOpen = false;
      await refreshBootstrap();
      render();
      toast("API key created.");
    } catch (error) {
      toast(error.message);
    }
    return;
  }

  if (form.matches("[data-settings-form]")) {
    event.preventDefault();
    const fd = new FormData(form);
    try {
      await apiPost("/api/settings", {
        full_name: fd.get("full_name"),
        email: fd.get("email"),
        bio: fd.get("bio"),
        timezone: fd.get("timezone"),
        default_language: fd.get("default_language"),
        default_language_label: languageLabel(fd.get("default_language")),
        default_model: fd.get("default_model"),
        email_on_complete: fd.get("email_on_complete") === "on",
        speaker_detection: fd.get("speaker_detection") === "on",
        product_updates: fd.get("product_updates") === "on",
      });
      await refreshBootstrap();
      render();
      toast("Settings saved.");
    } catch (error) {
      toast(error.message);
    }
  }
});

window.addEventListener("popstate", () => render());

async function init() {
  try {
    await refreshBootstrap();
    render();
  } catch (error) {
    app.innerHTML = `<div class="grid min-h-screen place-items-center px-6"><div class="max-w-lg rounded-[1.6rem] bg-white/82 p-8 text-center shadow-editorial"><h1 class="font-headline text-4xl">StoryToText failed to load</h1><p class="mt-4 text-sm leading-7 text-on-surface/62">${escapeHtml(error.message)}</p></div></div>`;
  }
}

function applyHistoryDomFilter() {
  if (window.location.pathname !== "/history") return;
  const query = state.historyQuery.trim().toLowerCase();
  const items = [...document.querySelectorAll("[data-history-item]")];
  if (!items.length) return;
  let visibleCount = 0;
  for (const item of items) {
    const status = item.dataset.status;
    const haystack = item.dataset.haystack || "";
    const visible =
      (state.historyFilter === "all" || state.historyFilter === status) &&
      (!query || haystack.includes(query));
    item.style.display = visible ? "" : "none";
    if (visible) visibleCount += 1;
  }
  const empty = document.getElementById("history-empty");
  if (empty) empty.style.display = visibleCount ? "none" : "";
}

init();
