import {
  ArrowRight,
  Check,
  CirclePlay,
  Crosshair,
  Github,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";

const landingVisual = "/assets/tactiframe-stadium-tracking-hero.png";

function Logo() {
  return (
    <span className="tf-logo" aria-label="TactiFrame">
      <span className="tf-mark"><span /></span>
      <span>Tacti<span>Frame</span></span>
    </span>
  );
}

const pillars = [
  { icon: Crosshair, title: "Pitch-aware perception", copy: "OpenCV turns frames into a structured view of players, zones, pressure, and space." },
  { icon: ScanSearch, title: "Evidence events & clips", copy: "Every insight stays attached to the event and the clip that supports it." },
  { icon: ShieldCheck, title: "Agent loop + coach approval", copy: "The agent proposes. The coach reviews, edits, and approves the next-session plan." },
];

const painPoints = [
  ["01", "Time consuming", "Hours of manual video review before the real conversation begins."],
  ["02", "Context gets lost", "Key moments live in separate clips, notes, and message threads."],
  ["03", "Hard to share", "Insights are difficult to communicate clearly across staff."],
];

function ProductFrame() {
  return (
    <div className="product-frame hero-frame">
      <img src={landingVisual} alt="Football stadium with pitch-aware tracking markers" />
      <div className="frame-overlay" />
      <div className="hero-frame-topline"><span><span className="status-dot" /> LIVE PITCH PERCEPTION</span><span className="frame-status">Model active</span></div>
      <div className="hero-motion-layer" aria-hidden="true">
        <svg className="motion-routes" viewBox="0 0 1000 560" preserveAspectRatio="none"><path className="motion-route route-one" d="M180 420 C300 260 420 340 570 230 S810 170 930 245" /><path className="motion-route route-two" d="M250 140 C350 230 400 170 520 270 S750 390 855 285" /></svg>
        <span className="motion-player player-one" /><span className="motion-player player-two" /><span className="motion-player player-three" /><span className="motion-player player-four" />
        <span className="motion-ball" /><span className="motion-pulse pulse-one" /><span className="motion-pulse pulse-two" />
      </div>
      <div className="hero-frame-caption"><span>TRACKING LAYER / 24 PLAYERS</span><strong>Movement paths detected</strong><small>Live tactical overlay · signal confidence 92%</small></div>
    </div>
  );
}

export default function Home() {
  return (
    <div className="tf-site">
      <header className="tf-nav">
        <a href="#top"><Logo /></a>
        <nav><a href="#product">Product</a><a href="#how-it-works">How it works</a></nav>
        <a className="button button-green button-small" href="/workspace">Open Workspace <ArrowRight size={15} /></a>
      </header>

      <main id="top">
        <section className="tf-hero shell">
          <div className="hero-copy">
            <div className="eyebrow"><span className="status-dot" /> FOOTBALL ANALYTICS / RESEARCH DEMO</div>
            <h1>Agentic vision for <em>opposition analysis.</em></h1>
            <p className="hero-sub">OpenCV turns match video into pitch-aware events. An agent reasons over clips and asks the coach to approve the plan.</p>
            <div className="hero-actions"><a className="button button-green" href="/workspace">Open Workspace <ArrowRight size={17} /></a><a className="button button-ghost" href="#how-it-works"><CirclePlay size={17} /> Watch demo</a></div>
            <div className="hero-meta"><span>Built for opposition analysts</span><span>Evidence-linked outputs</span><span>Coach in the loop</span></div>
          </div>
          <ProductFrame />
        </section>

        <section className="problem-section shell" id="product">
          <div className="section-kicker">THE PROBLEM</div>
          <div className="problem-grid"><div><h2>Analysts spend hours finding the right moments. <em>Context gets lost.</em></h2><p>Match video is long and complex. TactiFrame is designed around the moment that matters: turning footage into a shared, defensible football decision.</p></div><div className="pain-grid">{painPoints.map(([n, title, copy]) => <article className="pain-card" key={n}><span>{n}</span><h3>{title}</h3><p>{copy}</p></article>)}</div></div>
        </section>

        <section className="pillars-section shell"><div className="section-kicker">A NEW WAY TO WORK</div><h2>From video to <em>tactical decisions.</em></h2><div className="pillar-grid">{pillars.map(({ icon: Icon, title, copy }) => <article className="pillar-card" key={title}><Icon size={21} /><h3>{title}</h3><p>{copy}</p></article>)}</div></section>

        <section className="workspace-preview shell"><div className="preview-copy"><div className="section-kicker">SEE IT IN ACTION</div><h2>One workspace for <em>evidence, reasoning, and approval.</em></h2><p>Timeline events, tactical video, agent chat, and the next-session plan stay in one focused view.</p><a className="text-link" href="/workspace">Open the workspace <ArrowRight size={16} /></a></div><div className="preview-panel"><div className="preview-bar"><Logo /><span className="frame-status">Processed</span><button>Approve plan <Check size={14} /></button></div><div className="preview-columns"><div className="preview-list"><small>EVENTS TIMELINE</small>{["Pressure", "Zone density", "Turnover", "Progressive pass"].map((x, i) => <div className={i === 2 ? "selected" : ""} key={x}><b>{x}</b><span>00:{[14,29,41,62][i]}.36</span></div>)}</div><div className="preview-pitch"><div className="pitch-line pitch-mid" /><div className="pitch-line pitch-box left" /><div className="pitch-line pitch-box right" /><i className="player p1" /><i className="player p2" /><i className="player p3 green" /><i className="player p4 green" /><span className="route route-a" /></div><div className="preview-chat"><small>AGENT VISION CHAT</small><p>“High press creates turnovers in the right channel.”</p><div className="chat-event">Event #14 · Turnover</div><div className="chat-input">Ask about this match… <ArrowRight size={14} /></div></div></div></div></section>

        <section className="how-section shell" id="how-it-works"><div className="section-kicker">HOW IT WORKS</div><div className="steps">{[["01", "Process clip", "Drop in match video."], ["02", "Extract events", "OpenCV maps the pitch and finds moments."], ["03", "Ask agent", "Reason over evidence, not vibes."], ["04", "Approve plan", "Coach edits and signs off the next move."]].map(([n, title, copy]) => <article key={n}><span>{n}</span><div><h3>{title}</h3><p>{copy}</p></div><ArrowRight size={17} /></article>)}</div></section>

        <section className="audience-section shell"><div><div className="section-kicker">BUILT FOR THE STAFF ROOM</div><h2>Useful anywhere the next decision <em>matters.</em></h2></div><div className="audience-list"><span><Users size={17} /> Opposition analysts</span><span><Sparkles size={17} /> Coaching staff</span><span><Crosshair size={17} /> Academies</span></div></section>
      </main>

      <footer className="tf-footer shell"><Logo /><div><span>Research demo · Not for commercial use</span><a href="https://github.com/ousssamarahmani/Tactiframe"><Github size={15} /> GitHub</a></div><span>Built with OpenCV · Agent reasoning · Coach approval</span></footer>
    </div>
  );
}
