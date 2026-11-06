/* Walking Pad UI — icons, mascot, components and screens.
   Pure functions: state in -> HTML string out. Shared by the real app and the design board. */
(function (W) {
  "use strict";
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const n = x => (x ?? 0).toLocaleString("en-US");
  const km = m => ((m || 0) / 1000).toFixed(2);
  const mmss = s => { s = Math.max(0, Math.round(s || 0)); const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), ss = s % 60;
    return h ? `${h}:${String(m).padStart(2, "0")}:${String(ss).padStart(2, "0")}` : `${m}:${String(ss).padStart(2, "0")}`; };

  /* ---------------- icons (24px grid, chunky filled style) ---------------- */
  const I = {
    flame: `<svg viewBox="0 0 24 24"><path fill="currentColor" d="M12.6 1.8c.6 3.3 3.1 4.9 4.6 7.2 1.2 1.8 1.6 3.4 1.6 5.1A6.8 6.8 0 0 1 12 21a6.8 6.8 0 0 1-6.8-6.9c0-2.4 1.1-4.3 2.6-5.6.2 1.7 1 2.9 2.1 3.4-.4-3.7.9-7 2.7-10.1z"/><path fill="#fff" fill-opacity=".55" d="M12.2 11.2c1.6 1.4 3.2 2.8 3.2 4.9a3.4 3.4 0 0 1-6.8 0c0-1.2.5-2.2 1.3-3 .2.9.7 1.5 1.3 1.7-.2-1.3.2-2.5 1-3.6z"/></svg>`,
    shield: `<svg viewBox="0 0 24 24"><path fill="currentColor" d="M12 2 4 5v6.1c0 5 3.4 9.3 8 10.9 4.6-1.6 8-5.9 8-10.9V5z"/><path fill="#fff" d="m10.6 15.6-3.3-3.3 1.6-1.6 1.7 1.7 4.6-4.6 1.6 1.6z"/></svg>`,
    today: `<svg viewBox="0 0 24 24"><path fill="currentColor" d="M3 11.2 12 3l9 8.2V21h-6.5v-6h-5v6H3z"/></svg>`,
    chart: `<svg viewBox="0 0 24 24"><rect x="3" y="12" width="4.5" height="9" rx="1.6" fill="currentColor"/><rect x="9.75" y="7" width="4.5" height="14" rx="1.6" fill="currentColor"/><rect x="16.5" y="3" width="4.5" height="18" rx="1.6" fill="currentColor"/></svg>`,
    medal: `<svg viewBox="0 0 24 24"><path fill="currentColor" d="M7 2h4l2 5h-4zM13 2h4l-2 5h-4z" opacity=".6"/><circle cx="12" cy="14.5" r="7" fill="currentColor"/><path fill="#fff" d="m12 10.6 1.2 2.4 2.6.4-1.9 1.8.5 2.6-2.4-1.2-2.4 1.2.5-2.6-1.9-1.8 2.6-.4z"/></svg>`,
    target: `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9.5" fill="currentColor"/><circle cx="12" cy="12" r="6" fill="#fff"/><circle cx="12" cy="12" r="2.8" fill="currentColor"/></svg>`,
    check: `<svg viewBox="0 0 24 24"><path fill="currentColor" d="m9.4 17.6-5.3-5.3 2.3-2.3 3 3 8.2-8.2 2.3 2.3z"/></svg>`,
    bolt: `<svg viewBox="0 0 24 24"><path fill="currentColor" d="M13.5 2 4.8 13.4h6L9.8 22l9.4-12.3h-6.3z"/></svg>`,
    clock: `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9.5" fill="currentColor"/><path fill="#000" fill-opacity=".38" d="M11 6.5h2v5l3.4 2-1 1.8L11 12.6z"/></svg>`,
    steps: `<svg viewBox="0 0 24 24"><ellipse cx="8" cy="7" rx="3.2" ry="4.4" fill="currentColor"/><ellipse cx="8.4" cy="14.4" rx="2.2" ry="2.4" fill="currentColor"/><ellipse cx="16" cy="11" rx="3.2" ry="4.4" fill="currentColor"/><ellipse cx="15.6" cy="18.4" rx="2.2" ry="2.4" fill="currentColor"/></svg>`,
    route: `<svg viewBox="0 0 24 24"><circle cx="6" cy="18" r="3" fill="currentColor"/><path fill="currentColor" d="M18 1.8a4.2 4.2 0 0 0-4.2 4.2c0 3 4.2 7 4.2 7s4.2-4 4.2-7A4.2 4.2 0 0 0 18 1.8m0 5.7A1.5 1.5 0 1 1 18 4.5a1.5 1.5 0 0 1 0 3"/><path fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-dasharray="1 4" d="M8.5 16.5c3-1.5 2.5-4 5.5-5.5"/></svg>`,
    drop: `<svg viewBox="0 0 24 24"><path fill="currentColor" d="M12 2.5s-6.5 7.3-6.5 11.8a6.5 6.5 0 0 0 13 0C18.5 9.8 12 2.5 12 2.5"/></svg>`,
    crown: `<svg viewBox="0 0 24 24"><path fill="currentColor" d="m2.5 7.5 5 4 4.5-7 4.5 7 5-4-2 11h-15z"/><rect x="4.5" y="19.5" width="15" height="2.5" rx="1" fill="currentColor"/></svg>`,
    pad: `<svg viewBox="0 0 24 24"><rect x="2" y="9" width="20" height="8" rx="3" fill="currentColor"/><rect x="4.5" y="11.3" width="15" height="3.4" rx="1.7" fill="#fff" opacity=".5"/><rect x="4" y="17" width="3" height="3" rx="1" fill="currentColor"/><rect x="17" y="17" width="3" height="3" rx="1" fill="currentColor"/></svg>`,
    moon: `<svg viewBox="0 0 24 24"><path fill="currentColor" d="M15.5 3a9 9 0 1 0 5.5 15.3A7.5 7.5 0 0 1 15.5 3"/></svg>`,
    plane: `<svg viewBox="0 0 24 24"><path fill="currentColor" d="M21 15.5v-2l-8-5V3.3a1.5 1.5 0 0 0-3 0v5.2l-8 5v2l8-2.5v5.2L8 19.5V21l3.5-1 3.5 1v-1.5l-2-1.3V13z"/></svg>`,
    bed: `<svg viewBox="0 0 24 24"><path fill="currentColor" d="M2 6h2.5v7H11V8h7a4 4 0 0 1 4 4v8h-2.5v-3h-15v3H2z"/><circle cx="7.5" cy="10" r="2.3" fill="currentColor"/></svg>`,
    bell: `<svg viewBox="0 0 24 24"><path fill="currentColor" d="M12 2.5a6.5 6.5 0 0 0-6.5 6.5v4.3L3.5 17v1h17v-1l-2-3.7V9A6.5 6.5 0 0 0 12 2.5M9.5 19.5a2.5 2.5 0 0 0 5 0z"/></svg>`,
    gear: `<svg viewBox="0 0 24 24"><path fill="currentColor" d="m19.4 13 .1-1-.1-1 2.1-1.6-2-3.5-2.5 1a7.5 7.5 0 0 0-1.7-1L15 2.5h-4l-.4 2.6a7.5 7.5 0 0 0-1.7 1l-2.5-1-2 3.5L6.6 11l-.1 1 .1 1-2.1 1.6 2 3.5 2.5-1c.5.4 1.1.7 1.7 1l.4 2.6h4l.4-2.6c.6-.3 1.2-.6 1.7-1l2.5 1 2-3.5zM12 15.5a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7"/></svg>`,
    play: `<svg viewBox="0 0 24 24"><path fill="currentColor" d="M7 4.5v15l12.5-7.5z"/></svg>`,
    gift: `<svg viewBox="0 0 24 24"><rect x="3" y="9" width="18" height="4" rx="1" fill="currentColor"/><rect x="4.5" y="13" width="15" height="8" rx="1" fill="currentColor"/><rect x="10.8" y="9" width="2.4" height="12" fill="#fff" opacity=".6"/><path fill="currentColor" d="M12 9C10 4.5 6 5 6.5 7.4 7 9 12 9 12 9m0 0c2-4.5 6-4 5.5-1.6C17 9 12 9 12 9"/></svg>`,
  };

  /* ---------------- mascot: "Khatwa", a little walking bean ---------------- */
  function mascot(mood = "happy") {
    const eyes = mood === "sleepy"
      ? `<path d="M41 54q6 4 12 0M67 54q6 4 12 0" stroke="#2B2D30" stroke-width="4" fill="none" stroke-linecap="round"/>`
      : `<ellipse cx="47" cy="52" rx="7" ry="9" fill="#fff"/><ellipse cx="73" cy="52" rx="7" ry="9" fill="#fff"/><circle cx="48.5" cy="54" r="4" fill="#2B2D30"/><circle cx="74.5" cy="54" r="4" fill="#2B2D30"/><circle cx="50" cy="52" r="1.4" fill="#fff"/><circle cx="76" cy="52" r="1.4" fill="#fff"/>`;
    const mouth = mood === "sleepy" ? `<path d="M55 70q5 3 10 0" stroke="#2B2D30" stroke-width="3.5" fill="none" stroke-linecap="round"/>`
      : mood === "cheer" ? `<path d="M50 66q10 14 20 0z" fill="#7A2E12"/><path d="M54 71q6 4 12 0" fill="#FF7A6B"/>`
      : `<path d="M51 67q9 9 18 0" stroke="#2B2D30" stroke-width="4" fill="none" stroke-linecap="round"/>`;
    const arms = mood === "cheer"
      ? `<path d="M26 60 12 34" stroke="#2F9A38" stroke-width="9" stroke-linecap="round"/><path d="M94 60l14-26" stroke="#2F9A38" stroke-width="9" stroke-linecap="round"/>`
      : `<path d="M27 66 17 80" stroke="#2F9A38" stroke-width="9" stroke-linecap="round"/><path d="M93 66l10 14" stroke="#2F9A38" stroke-width="9" stroke-linecap="round"/>`;
    return `<svg class="mascot" viewBox="0 0 120 130" role="img" aria-label="Khatwa the walking bean">
      ${arms}
      <path d="M44 100v14M76 100v14" stroke="#2F9A38" stroke-width="9" stroke-linecap="round"/>
      <path d="M33 112h20a6 6 0 0 1 0 12H31a5 5 0 0 1 2-12zM67 112h20a5 5 0 0 1 2 12H67a6 6 0 0 1 0-12z" fill="#FF8A1F"/>
      <path d="M33 120h22M67 120h22" stroke="#fff" stroke-width="2.5"/>
      <ellipse cx="60" cy="62" rx="36" ry="44" fill="#3FBF4A"/>
      <ellipse cx="60" cy="76" rx="22" ry="22" fill="#7FDB86"/>
      <path d="M38 30q8-14 22-14" stroke="#fff" stroke-opacity=".45" stroke-width="5" fill="none" stroke-linecap="round"/>
      ${eyes}${mouth}
      <ellipse cx="38" cy="66" rx="5" ry="3" fill="#FF9F8F" opacity=".7"/><ellipse cx="82" cy="66" rx="5" ry="3" fill="#FF9F8F" opacity=".7"/>
    </svg>`;
  }

  /* ---------------- medal art ---------------- */
  function medalSvg(kind, label) {
    const C = { flame: ["#FF8A1F", "#E06B00", "#FFD19E"], sun: ["#FFC52E", "#E0A100", "#FFE9A6"], leaf: ["#3FBF4A", "#2F9A38", "#BFEFC3"],
                sky: ["#22A6F2", "#0C84CB", "#B5E2FB"], berry: ["#9B6BFF", "#7444E0", "#D9C8FF"] }[kind] || ["#ccc", "#aaa", "#eee"];
    return `<svg viewBox="0 0 80 80"><path d="M40 3 72 21v38L40 77 8 59V21z" fill="${C[1]}"/><path d="M40 8 67 23.5v33L40 72 13 56.5v-33z" fill="${C[0]}"/>
      <path d="M40 8 67 23.5v8L40 16 13 31.5v-8z" fill="#fff" opacity=".22"/>
      <text x="40" y="49" text-anchor="middle" font-family="Nunito" font-weight="1000" font-size="${String(label).length > 3 ? 17 : 22}" fill="#fff">${esc(label)}</text></svg>`;
  }

  /* ---------------- extra icons ---------------- */
  Object.assign(I, {
    users: `<svg viewBox="0 0 24 24"><circle cx="8.5" cy="8" r="3.6" fill="currentColor"/><path fill="currentColor" d="M1.5 20c0-4 3.1-6.5 7-6.5s7 2.5 7 6.5z"/><circle cx="17" cy="9" r="2.8" fill="currentColor" opacity=".7"/><path fill="currentColor" opacity=".7" d="M16.2 13.6c3.4-.3 6.3 1.8 6.3 5.4v1h-5.3c0-2.6-.4-4.8-1-6.4"/></svg>`,
    map: `<svg viewBox="0 0 24 24"><path fill="currentColor" d="M2 5.5 8 3l8 3 6-2.5v15L16 21l-8-3-6 2.5z" opacity=".35"/><path fill="currentColor" d="M8 3v15l8 3V6z"/></svg>`,
    plus: `<svg viewBox="0 0 24 24"><path fill="currentColor" d="M10.5 4h3v6.5H20v3h-6.5V20h-3v-6.5H4v-3h6.5z"/></svg>`,
    trash: `<svg viewBox="0 0 24 24"><path fill="currentColor" d="M9 2.5h6l1 2H20v2.5H4V4.5h4zM5.5 8.5h13l-1 13h-11z"/></svg>`,
    copy: `<svg viewBox="0 0 24 24"><rect x="8" y="8" width="13" height="13" rx="3" fill="currentColor"/><path fill="currentColor" opacity=".45" d="M6 16H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1H9a3 3 0 0 0-3 3z"/></svg>`,
    star: `<svg viewBox="0 0 24 24"><path fill="currentColor" d="m12 2.5 2.9 6 6.6.8-4.9 4.6 1.3 6.6L12 17.3l-5.9 3.2 1.3-6.6-4.9-4.6 6.6-.8z"/></svg>`,
  });

  /* ---------------- metric helpers ---------------- */
  const UNIT = { steps: "steps", minutes: "min", km: "km", allsteps: "steps" };
  const MNAME = { steps: "Pad steps", minutes: "Minutes", km: "Distance (km)", allsteps: "All-day steps (Apple Health)" };
  function fv(metric, v) {
    v = +v || 0;
    if (metric === "steps" || metric === "allsteps") return Math.round(v).toLocaleString("en-US");
    if (metric === "km") return v < 10 ? v.toFixed(2).replace(/\.?0+$/, "") || "0" : v.toFixed(1).replace(/\.0$/, "");
    return String(Math.round(v * 10) / 10);
  }
  const fu = (metric, v) => `${fv(metric, v)} ${UNIT[metric]}`;
  const tv = s => (s.today.value ?? s.today.min);              // today's value of the main metric
  const lm = s => (s.goal.metric || "minutes");
  function landmark(key, size = 40) {
    const L = window.WalkLandmarks && window.WalkLandmarks.icons && window.WalkLandmarks.icons[key];
    if (L) return `<span class="lmk" style="width:${size}px;height:${size}px">${L}</span>`;
    return `<span class="lmk lmk-fb" style="width:${size}px;height:${size}px">${I.route}</span>`;
  }

  /* ---------------- components ---------------- */
  function ring(v, goal, tiny, size = 260, stroke = 26) {
    const r = (size - stroke) / 2, pct = Math.min(1, v / goal), over = Math.max(0, Math.min(1, (v - goal) / goal));
    const tinyPct = Math.min(1, tiny / goal);
    return `<svg class="ring" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" data-stroke="${stroke}">
      <circle class="trk" cx="${size/2}" cy="${size/2}" r="${r}" stroke-width="${stroke}"/>
      <circle class="tiny" cx="${size/2}" cy="${size/2}" r="${r}" stroke-width="${stroke}" pathLength="100" stroke-dasharray="${tinyPct*100} 100"/>
      ${pct > 0 ? `<circle class="arc" cx="${size/2}" cy="${size/2}" r="${r}" stroke-width="${stroke}" pathLength="100" stroke-dasharray="${Math.max(.5, pct*100)} 100"/>` : ""}
      ${over > 0 ? `<circle class="arc over" cx="${size/2}" cy="${size/2}" r="${r}" stroke-width="${stroke}" pathLength="100" stroke-dasharray="${over*100} 100"/>` : ""}
      <circle class="tick" cx="${size/2}" cy="${size/2}" r="${r}" stroke-width="${stroke+2}" pathLength="100" stroke-dasharray="0.6 99.4" stroke-dashoffset="-${tinyPct*100}"/>
    </svg>`;
  }
  function goalRing(s, size) {
    const m = lm(s), v = tv(s), g = s.goal, stroke = size > 200 ? 26 : 20;
    const big = fv(m, Math.floor(m === "km" ? v * 100 : v) / (m === "km" ? 100 : 1));
    const fs = Math.round(size * (big.length <= 3 ? .24 : big.length <= 5 ? .19 : .155));
    const em = v >= g.goal ? (v >= g.stretch ? ["Goal done", "Stretch done too"] : ["Goal done", `${fv(m, g.stretch - v)} to stretch`])
      : v >= g.tiny ? [`${fv(m, g.goal - v)} ${UNIT[m]}`, "to your goal"] : [`${fv(m, g.tiny - v)} ${UNIT[m]}`, "keeps your streak"];
    // the centre text is confined to the inner circle (see .ringc padding) so it never touches the ring
    return `<div class="ringwrap" style="width:${size}px;height:${size}px">${ring(v, g.goal, g.tiny, size, stroke)}
      <div class="ringc" style="--inner:${size - 2 * stroke}px"><b class="num" style="font-size:${fs}px">${big}</b><small>of ${fu(m, g.goal)}</small><em>${em[0]}<br>${em[1]}</em></div></div>`;
  }
  const chip = (cls, icon, text, title) => `<span class="chip ${cls}" title="${esc(title || "")}">${I[icon]}<span class="num">${text}</span></span>`;
  function chips(s) {
    return `${chip(s.streak.days ? "flame" : "dim", "flame", s.streak.days, `${s.streak.days}-day streak · best ${s.streak.best}`)}
            ${chip("shield", "shield", s.streak.shields, `${s.streak.shields} rest shields`)}`;
  }
  function tiers(s) {
    const t = tv(s), g = s.goal, m = lm(s);
    const st = v => t >= v ? "done" : "next";
    return `<div class="tiers"><span class="tier ${st(g.tiny)}">Tiny ${fu(m, g.tiny)}${t >= g.tiny ? " ✓" : ""}</span>
      <span class="tier ${t >= g.tiny ? st(g.goal) : ""}">Goal ${fu(m, g.goal)}${t >= g.goal ? " ✓" : ""}</span>
      <span class="tier ${t >= g.goal ? st(g.stretch) : ""}">Stretch ${fu(m, g.stretch)}${t >= g.stretch ? " ✓" : ""}</span></div>`;
  }
  function stats(s, src) {
    const x = src || s.today;
    return `<div class="stats">
      <div class="stat"><b class="num">${n(x.steps)}</b><span>steps</span></div>
      <div class="stat"><b class="num">${km(x.distance_m)}</b><span>km</span></div>
      <div class="stat"><b class="num">${n(x.kcal)}</b><span>kcal (estimate)</span></div>
      <div class="stat"><b class="num">${x.sessions ?? 1}</b><span>${(x.sessions ?? 1) === 1 ? "walk" : "walks"} today</span></div></div>`;
  }
  function goalsCard(s) {
    if (!s.goals || !s.goals.length) return "";
    return `<div class="card"><div class="between"><h3>Your goals</h3><a class="sub" data-go="goals" style="color:var(--sky-d)">Edit</a></div>
      ${s.goals.map(g => `<div class="goalrow">
        <div class="between"><b>${g.primary ? `<span class="mainbadge">${I.flame}Main</span>` : ""}${esc(g.title)}</b><span class="num ${g.done ? "ok" : ""}">${g.done ? "Done" : `${fv(g.metric, g.value)} / ${fv(g.metric, g.target)}`}</span></div>
        <div class="bar ${g.done ? "leaf" : "sky"}" style="height:12px"><i style="width:${g.pct}%"></i></div></div>`).join("")}</div>`;
  }
  function week(s) {
    const ic = { goal: I.check, tiny: I.check, shield: I.shield };
    const done = s.weekDone ?? s.week.filter(d => d.state === "goal").length;
    return `<div class="card"><div class="between"><h3>This week</h3><span class="sub num">${done} of ${s.weekGoal} goal days</span></div>
      <div class="week">${s.week.map(d => `<div class="wd ${d.state}"><i>${ic[d.state] || ""}</i>${d.d}</div>`).join("")}</div>
      <div class="weekbar"><i style="width:${Math.min(100, done / s.weekGoal * 100)}%"></i></div>
      <p class="sub" style="margin:10px 0 0">${esc(s.weekNote)}</p></div>`;
  }
  function monthCard(s) {
    const m = s.month;
    return `<div class="card"><div class="between"><h3>${esc(m.name)} challenge</h3>${medalSvg("sun", m.target).replace("<svg", '<svg width="44" height="44"')}</div>
      <p class="sub" style="margin:-4px 0 12px">Hit your main goal on ${m.target} different days</p>
      <div class="bar"><i style="width:${m.done / m.target * 100}%"></i></div>
      <div class="between" style="margin-top:8px"><span class="sub num">${m.done} / ${m.target} days</span><span class="sub">${m.daysLeft} days left</span></div></div>`;
  }
  function nextCard(s) {
    return `<div class="card tight"><div class="row">${medalSvg("flame", s.next.label).replace("<svg", '<svg width="58" height="58"')}
      <div><span class="eyebrow">Next medal</span><b style="display:block;font-size:17px">${esc(s.next.title)}</b><span class="sub">${esc(s.next.hint)}</span></div></div></div>`;
  }
  function padChip(s) {
    return s.pad.connected ? `<div class="padchip"><span class="dot on"></span><span>Pad connected</span><span style="margin-left:auto;color:var(--muted)">${esc(s.pad.name)}</span></div>`
                           : `<div class="padchip"><span class="dot"></span>Pad off · searching</div>`;
  }
  function journeyMini(s) {
    const J = s.journey; if (!J || !J.track) return "";
    const pct = Math.min(100, J.done / Math.max(.1, J.total) * 100);
    return `<div class="card tight"><div class="between"><span class="eyebrow">Walk across Saudi Arabia</span><button class="btn ghost mini" data-act="map">${I.map}Map</button></div>
      <div class="row" style="margin:8px 0 10px">${landmark(J.nextKey, 52)}<div><b style="display:block">${J.complete ? "Track complete" : `Next: ${esc(J.next)}`}</b><span class="sub">${J.complete ? esc(J.track.name) : `${J.toNext} km to go · ${esc(J.track.name)}`}</span></div></div>
      <div class="bar leaf" style="height:12px"><i style="width:${pct}%"></i></div></div>`;
  }

  function syncPill(s) {
    const R = s.remote;
    if (R && R.stale) return `<div class="from-pc stale"><span class="dot"></span>Your PC was last seen ${esc(R.ago)} ago. Showing that data.</div>`;
    return `<div class="from-pc"><span class="dot ${s.pad.connected ? "on" : ""}"></span>${s.pad.connected ? (R ? "Live from your PC · pad connected" : "Pad connected") : (R ? "Synced from your PC · pad off" : "Pad off")}</div>`;
  }

  /* ---------------- shells ---------------- */
  const NAV = [["today", "today", "Today"], ["progress", "chart", "Progress"], ["awards", "medal", "Awards"], ["community", "users", "Community"], ["goals", "target", "Goals"]];
  function shell(d, active, s, body, opts = {}) {
    if (d === "phone") {
      return `<div class="app phone">
        <div class="ptop"><div class="brand" style="padding:0;font-size:20px">${mascot().replace('class="mascot"', 'style="width:34px;height:34px"')}</div>
          <div class="row" style="gap:8px">${chips(s)}</div></div>
        <div class="pbody">${opts.fromPc !== false ? syncPill(s) : ""}${body}</div>
        <nav class="tabs five">${NAV.map(([k, ic, l]) => `<a class="tab ${k === active ? "on" : ""}" data-go="${k}">${I[ic]}${l}</a>`).join("")}</nav></div>`;
    }
    return `<div class="app desktop">
      <aside class="rail"><div class="brand">${mascot().replace('class="mascot"', "")}<span>Walking Pad</span></div>
        ${NAV.map(([k, ic, l]) => `<a class="nav ${k === active ? "on" : ""}" data-go="${k}" tabindex="0">${I[ic]}${l}</a>`).join("")}
        ${padChip(s)}</aside>
      <main class="main ${opts.single ? "" : "two"}">${s.remote && s.remote.stale ? `<div class="banner sky" style="grid-column:1/-1">${I.clock}<div><b>Your PC is offline</b>Last update ${esc(s.remote.ago)} ago. Changes you make wait until it's back.</div></div>` : ""}${body}</main></div>`;
  }

  /* ---------------- screens ---------------- */
  const S = {};

  S.today = (s, d) => {
    const banner = s.banner ? banners[s.banner](s) : "";
    const cta = s.pad.connected && s.pad.control
      ? `<div class="row" style="gap:14px;flex-wrap:wrap"><button class="btn sky" data-act="padstart">${I.play} Start walking</button><span class="sub">Or press start on the pad's remote</span></div>`
      : s.pad.connected
      ? `<div class="row" style="gap:14px;flex-wrap:wrap"><span class="btn sky" aria-hidden="true">${I.pad} Step on to start</span><span class="sub">Walking starts the session by itself</span></div>`
      : `<div class="row" style="gap:14px;flex-wrap:wrap"><span class="btn ghost">${I.pad} Turn on the pad</span><span class="sub">It connects by itself in ~20 s</span></div>`;
    const v = tv(s), greet = v >= s.goal.goal ? "Goal done today." : v >= s.goal.tiny ? "Streak safe. Keep going?" : s.greeting;
    const hero = `<div class="card"><div class="hero" style="${d === "phone" ? "grid-template-columns:1fr;justify-items:center;text-align:center;gap:16px" : ""}">
        ${goalRing(s, d === "phone" ? 230 : 280)}
        <div><span class="eyebrow">${esc(s.dateLabel)}</span><h2>${esc(greet)}</h2><p>${esc(s.heroNote)}</p>${tiers(s)}${cta}</div></div></div>`;
    if (d === "phone") return shell(d, "today", s, `${banner}${hero}${goalsCard(s)}${week(s)}${stats(s)}${journeyMini(s)}${nextCard(s)}${monthCard(s)}`);
    return shell(d, "today", s, `<div class="col">${banner}${hero}${stats(s)}${week(s)}</div>
      <div class="col"><div class="card tight between"><span class="eyebrow">Streak</span><div class="row" style="gap:8px">${chips(s)}</div></div>${goalsCard(s)}${journeyMini(s)}${nextCard(s)}${monthCard(s)}</div>`);
  };

  const banners = {
    comeback: s => `<div class="banner flame">${I.gift}<div><b>Welcome back. Today's walk counts double.</b>Comeback day: hitting your main goal today counts twice toward your week and your month. ${fu(lm(s), s.goal.tiny)} starts a new streak.</div></div>`,
    shield: s => `<div class="banner berry">${I.shield}<div><b>A rest shield saved your ${s.streak.days}-day streak.</b>Yesterday was covered automatically. You have ${s.streak.shields} left; earn another with 7 walking days.</div></div>`,
    padoff: s => `<div class="banner sky">${mascot("sleepy").replace('class="mascot"', 'style="width:54px;height:54px;flex:none"')}<div><b>Your pad is asleep.</b>Switch it on and it connects by itself. Your history is safe on this PC.</div></div>`,
  };

  S.live = (s, d) => {
    const L = s.live, m = lm(s), toast = s.toast ? `<div class="toast" style="top:${d === "phone" ? 90 : 26}px">${I[s.toast.icon]}${esc(s.toast.text)}</div>` : "";
    const v = tv(s), left = Math.max(0, s.goal.goal - v);
    const body = `
      <div class="between"><span class="pace">${I.bolt}<span class="num">${(+L.speed).toFixed(1)} km/h</span></span><span class="pace">${I.clock}<span class="num">${mmss(L.elapsed)}</span>&nbsp;this walk</span></div>
      <div style="display:grid;${d === "phone" ? "justify-items:center;gap:18px" : "grid-template-columns:auto 1fr;gap:48px;align-items:center"}">
        ${goalRing(s, d === "phone" ? 250 : 340)}
        <div style="${d === "phone" ? "text-align:center" : ""}">
          <span class="eyebrow" style="color:#D6EFFF">${left > 0 ? "To today's goal" : "Today's goal"}</span>
          <div class="livebig num">${left > 0 ? `${fv(m, left)}<span class="unit">${UNIT[m]} to go</span>` : `Done<span class="unit">bonus time now</span>`}</div>
          <p style="font-size:20px;font-weight:900;margin:8px 0 18px">${esc(s.etaText || (left > 0 ? "" : "Everything from here counts toward stretch."))}</p>
          <div class="bar sky" style="background:rgba(255,255,255,.2);height:18px"><i style="width:${Math.min(100, v / s.goal.goal * 100)}%;background:#fff"></i></div>
          <div class="between" style="margin-top:8px;font-weight:900;font-size:13px;opacity:.9"><span>Tiny${v >= s.goal.tiny ? " ✓" : ""}</span><span>25%</span><span>50%</span><span>75%</span><span>Goal ${fv(m, s.goal.goal)}</span></div>
        </div></div>
      ${padControls(s, d)}
      ${stats(s, { steps: L.steps, distance_m: L.distance_m, kcal: L.kcal, sessions: s.today.sessions })}
      <div class="between" style="flex-wrap:wrap;gap:10px"><span class="pace">${I.flame} ${v >= s.goal.tiny ? "Streak safe for today" : `${fu(m, s.goal.tiny - v)} to keep your streak`}</span><span class="pace" style="opacity:.85">Stops by itself when you step off</span></div>`;
    const wrap = `<div class="live" style="position:relative;display:grid;gap:${d === "phone" ? 18 : 26}px;align-content:start;padding:${d === "phone" ? "18px 16px 26px" : "34px 44px"};min-height:100%">${toast}${body}</div>`;
    if (d === "phone") return `<div class="app phone" style="grid-template-rows:auto 1fr"><div class="ptop live" style="padding-bottom:0"><span class="pace">${I.pad} Live</span><div class="row" style="gap:8px">${chips(s)}</div></div>${wrap}</div>`;
    return `<div class="app desktop" style="grid-template-columns:1fr">${wrap}</div>`;
  };

  function padControls(s, d) {
    const P = s.pad || {};
    if (!P.control) return "";
    const R = P.speedRange || { min: 1, max: 6, inc: .5 };
    const cur = P.paused ? 0 : (+s.live.speed || 0), tgt = P.targetSpeed || cur;
    const presets = [["Typing", 2.0], ["Calls", 3.5], ["Brisk", 5.0]].filter(([, v]) => v >= R.min && v <= R.max);
    const dis = P.paused ? "disabled" : "";
    return `<div class="padctl ${P.paused ? "paused" : ""}">
      ${P.paused ? `<div class="pausedtag">${I.clock} Paused. Your walk is kept; resume when you're ready.</div>` : ""}
      <div class="padrow">
        <div class="spd"><button class="round" data-act="padspeed" data-v="${Math.max(R.min, tgt - R.inc)}" aria-label="Slower" ${dis}>−</button>
          <div class="spdval"><b class="num">${cur.toFixed(1)}</b><small>km/h${tgt && Math.abs(tgt - cur) > .05 && !P.paused ? ` → ${tgt.toFixed(1)}` : ""}</small></div>
          <button class="round" data-act="padspeed" data-v="${Math.min(R.max, tgt + R.inc)}" aria-label="Faster" ${dis}>+</button></div>
        <div class="presets">${presets.map(([l, v]) => `<button class="preset ${Math.abs(tgt - v) < .05 && !P.paused ? "on" : ""}" data-act="padspeed" data-v="${v}" ${dis}><b class="num">${v.toFixed(1)}</b>${l}</button>`).join("")}</div>
        <div class="acts">${P.paused ? `<button class="btn" data-act="padresume">${I.play} Resume</button>` : `<button class="btn ghostw" data-act="padpause">Pause</button>`}
          <button class="btn stop" data-act="padstop">Stop</button></div>
      </div>
      ${d === "desktop" ? `<p class="keys">Keys: <kbd>↑</kbd> <kbd>↓</kbd> speed · <kbd>Space</kbd> pause / resume</p>` : ""}</div>`;
  }

  S.countdown = (s, d) => `<div class="app ${d}" style="${d === "desktop" ? "grid-template-columns:1fr" : "grid-template-rows:1fr"}"><div class="countdown">
      ${mascot("happy").replace('class="mascot"', 'style="width:120px;height:120px"')}
      <p class="eyebrow" style="color:#E4F5FF">Step on the pad now</p><div class="cdnum num">${s.countdownN}</div>
      <p>The belt starts slowly. Change the speed any time from the next screen.</p>
      <button class="btn ghostw" data-act="padcancel">Cancel</button></div></div>`;

  S.celebrate = (s, d) => {
    const colors = ["#FFC52E", "#FF8A1F", "#22A6F2", "#fff", "#9B6BFF"];
    let conf = ""; for (let i = 0; i < 46; i++) { const x = (i * 37) % 100, y = (i * 53) % 90, r = (i * 47) % 180;
      conf += `<i style="left:${x}%;top:${y}%;background:${colors[i % 5]};transform:rotate(${r}deg)"></i>`; }
    const big = s.celebration === "milestone", m = lm(s);
    const head = big ? `${s.streak.days}-day streak!` : "Goal done!";
    const line = big ? (MILESTONE_LINES[s.streak.days] || "Look at that streak. This is a habit now.")
                     : `${fu(m, s.goal.goal)} today. Your streak is ${s.streak.days} day${s.streak.days === 1 ? "" : "s"}.`;
    const inner = `<div class="confetti">${conf}</div>${mascot("cheer")}
      ${big ? `<div style="justify-self:center">${medalSvg("flame", s.streak.days).replace("<svg", '<svg width="110" height="110"')}</div>` : ""}
      <h1>${head}</h1><p>${line}</p>
      <div class="sumrow">${[[n(s.today.steps), "steps"], [`${Math.floor(s.today.min)} min`, "today"], [`${km(s.today.distance_m)} km`, "distance"]].map(([a, b]) => `<div><b class="num">${a}</b><span>${b}</span></div>`).join("")}</div>
      <div style="margin-top:14px"><button class="btn" data-act="dismiss" style="background:#fff;color:var(--leaf-d);box-shadow:0 5px 0 #CFEFD1">Keep walking</button></div>`;
    return `<div class="app ${d}" style="${d === "desktop" ? "grid-template-columns:1fr" : "grid-template-rows:1fr"}"><div class="celebrate" style="padding:24px">${inner}</div></div>`;
  };
  const MILESTONE_LINES = { 3: "Three days in a row. The hardest part is behind you.", 7: "A week of walking. That's a real habit forming.",
    14: "Two weeks. Your body is starting to expect it.", 30: "A month of showing up. That's who you are now.",
    60: "Sixty days. Most habits are settled by now.", 100: "One hundred days. Rare company.", 365: "A full year. Remarkable." };

  S.summary = (s, d) => {
    const w = s.lastWalk;
    if (!w) return S.today(s, d);
    const body = `<div class="card" style="text-align:center;display:grid;gap:8px;justify-items:center">
        ${mascot("happy").replace('class="mascot"', 'style="width:110px;height:110px"')}
        <span class="eyebrow">Walk finished · ${esc(w.when)}</span><h2 style="margin:0;font-size:30px;font-weight:1000">${n(w.steps)} steps, nicely done</h2>
        <p class="sub" style="margin:0">${w.min} min · average ${w.avgSpeed} km/h · top ${w.topSpeed} km/h</p>
        <button class="btn sky" data-go="today" style="margin-top:8px">Back to today</button></div>
      ${stats(s, { steps: w.steps, distance_m: w.distance_m, kcal: w.kcal, sessions: s.today.sessions })}
      <div class="card"><h3>What this walk earned</h3>
        ${w.earned.map(e => `<div class="li"><span class="ic" style="background:var(--${e.c}-l);color:var(--${e.c === "leaf" ? "leaf-d" : e.c === "sun" ? "sun-d" : e.c})">${I[e.icon]}</span><div><b>${esc(e.title)}</b><span class="sub">${esc(e.sub)}</span></div>${e.end ? `<span class="end num">${esc(e.end)}</span>` : ""}</div>`).join("")}</div>
      <div class="card"><h3>Speed this walk</h3>${sparkline(w.trace, d === "phone" ? 330 : 640, 110)}</div>`;
    if (d === "phone") return shell(d, "today", s, body);
    return shell(d, "today", s, `<div class="col">${body}</div><div class="col">${goalsCard(s)}${week(s)}${nextCard(s)}</div>`);
  };

  function sparkline(pts, w, h) {
    if (!pts || pts.length < 2) pts = [0, 0];
    const max = Math.max(...pts, 1), step = w / (pts.length - 1);
    const p = pts.map((v, i) => `${i ? "L" : "M"}${(i * step).toFixed(1)},${(h - 8 - (v / max) * (h - 16)).toFixed(1)}`).join("");
    return `<svg width="100%" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" style="display:block"><path d="${p} L${w},${h} L0,${h}Z" fill="var(--sky-l)"/><path d="${p}" fill="none" stroke="var(--sky)" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/></svg>`;
  }

  function recordsCard(s, limit) {
    const rows = s.records.slice(0, limit || 99);
    return `<div class="card"><h3>Personal records</h3>${rows.length ? rows.map(r => `<div class="li"><span class="ic" style="background:var(--sun-l);color:var(--sun-d)">${I.crown}</span><div><b>${esc(r.title)}</b><span class="sub">${esc(r.when)}</span></div><span class="end num">${esc(r.value)}</span></div>`).join("")
      : `<p class="sub" style="margin:0">Your first walk sets your first records.</p>`}</div>`;
  }

  S.progress = (s, d) => {
    const mode = s.barMode || "week", metric = s.barMetric || lm(s);
    const daily = Array.isArray(s.daily) ? s.daily : s.daily[mode];
    const cal = `<div class="card"><div class="between"><h3>${esc(s.calendar.title)}</h3><span class="sub">${esc(s.calendar.legend)}</span></div>
      <div class="cal">${"SMTWTFS".split("").map(h => `<span class="h">${h}</span>`).join("")}${s.calendar.cells.map(c => `<span class="c ${c.s || ""}">${c.d || ""}</span>`).join("")}</div>
      <div class="row" style="gap:16px;margin-top:14px;flex-wrap:wrap;font-size:13px;color:var(--muted)"><span class="row" style="gap:6px"><i class="dot" style="background:var(--leaf)"></i>Goal day</span><span class="row" style="gap:6px"><i class="dot" style="background:var(--leaf-l);border:2px solid var(--leaf)"></i>Tiny walk</span><span class="row" style="gap:6px"><i class="dot" style="background:var(--berry-l);border:2px solid var(--berry)"></i>Rest shield</span></div></div>`;
    const life = `<div class="card"><h3>All time</h3><div class="stats" style="grid-template-columns:repeat(2,minmax(0,1fr))">
      ${s.lifetime.map(([v, l]) => `<div class="stat"><b class="num">${esc(v)}</b><span>${esc(l)}</span></div>`).join("")}</div></div>`;
    const avg = s.stats ? `<div class="card"><h3>Averages and totals</h3>${s.stats.map(([v, l]) => `<div class="li"><span class="ic" style="background:var(--sky-l);color:var(--sky-d)">${I.chart}</span><div><b>${esc(l)}</b></div><span class="end num">${esc(v)}</span></div>`).join("")}</div>` : "";
    const tab = (act, k, t, on) => `<button class="tier ${on ? "next" : ""}" data-act="${act}" data-v="${k}">${t}</button>`;
    const tabs = Array.isArray(s.daily) ? "" : `<div class="row" style="gap:6px;flex-wrap:wrap">${[["steps", "Steps"], ["min", "Minutes"], ["km", "Km"]].map(([k, t]) => tab("barmetric", k, t, (metric === "minutes" ? "min" : metric) === k)).join("")}
      <span style="width:8px"></span>${[["week", "Week"], ["month", "Month"]].map(([k, t]) => tab("bars", k, t, k === mode)).join("")}</div>`;
    const key = metric === "minutes" ? "min" : metric;
    const gmetric = lm(s) === "minutes" ? "min" : lm(s);
    const bars = `<div class="card"><div class="between" style="flex-wrap:wrap;gap:8px"><h3>${key === "steps" ? "Steps" : key === "km" ? "Kilometres" : "Minutes"} per day</h3>${tabs}</div>
      ${barChart(daily, key, key === gmetric ? s.goal.goal : null, key === gmetric ? s.goal.tiny : null, d === "phone" ? 330 : 620, 200)}</div>`;
    const heat = `<div class="card"><h3>The last 6 months</h3><div style="overflow:hidden"><div class="heat">${s.heat.map(l => `<i class="l${l < 0 ? "x" : l}"></i>`).join("")}</div></div><p class="sub" style="margin:10px 0 0">Every square is a day. Darker green = closer to your stretch level.</p></div>`;
    if (d === "phone") return shell(d, "progress", s, `${life}${bars}${avg}${cal}${recordsCard(s, 3)}`);
    return shell(d, "progress", s, `<div class="col">${bars}${heat}${cal}</div><div class="col">${life}${avg}${recordsCard(s)}</div>`);
  };

  function barChart(days, key, goal, tiny, w, h) {
    const vals = days.map(x => +(x[key] ?? x.min) || 0);
    const max = Math.max(goal ? goal * 1.4 : 0, ...vals, key === "steps" ? 1000 : key === "km" ? 1 : 10), bw = w / days.length, pb = 24;
    const fmt = v => key === "steps" ? (v >= 1000 ? (v / 1000).toFixed(1).replace(/\.0$/, "") + "k" : Math.round(v)) : key === "km" ? v.toFixed(1) : Math.round(v);
    const bars = days.map((x, i) => { const v = vals[i], bh = (v / max) * (h - pb - 14);
      const c = goal ? (v >= goal ? "var(--leaf)" : v >= tiny && v > 0 ? "#9BE09F" : "var(--line)") : (v > 0 ? "var(--sky)" : "var(--line)");
      return `<rect x="${i * bw + bw * .2}" y="${h - pb - Math.max(bh, 4)}" width="${bw * .6}" height="${Math.max(bh, 4)}" rx="${Math.min(7, bw * .25)}" fill="${c}"><title>${x.date || x.d}: ${fmt(v)}</title></rect>
        ${v > 0 && bw > 40 ? `<text x="${i * bw + bw / 2}" y="${h - pb - Math.max(bh, 4) - 6}" text-anchor="middle" font-size="11" font-weight="900" fill="var(--muted)">${fmt(v)}</text>` : ""}
        <text x="${i * bw + bw / 2}" y="${h - 6}" text-anchor="middle" font-size="12" font-weight="800" fill="var(--muted)">${x.d}</text>`; }).join("");
    const gl = goal ? (() => { const gy = h - pb - (goal / max) * (h - pb - 14);
      return `<line x1="0" x2="${w}" y1="${gy}" y2="${gy}" stroke="var(--sun-d)" stroke-width="2.5" stroke-dasharray="6 6"/><text x="${w}" y="${gy - 6}" text-anchor="end" font-size="12" font-weight="900" fill="var(--sun-d)">goal ${fmt(goal)}</text>`; })() : "";
    return `<svg width="100%" viewBox="0 0 ${w} ${h}" style="display:block">${bars}${gl}</svg>`;
  }

  function journeyCard(s) {
    const J = s.journey;
    if (!J || !J.track) return "";
    const pct = Math.min(100, J.done / Math.max(.1, J.total) * 100);
    return `<div class="card"><div class="between" style="flex-wrap:wrap;gap:10px"><h3 style="margin:0">Walk across Saudi Arabia</h3>
        <div class="row" style="gap:8px"><button class="btn ghost mini" data-act="map">${I.map}Map and tracks</button></div></div>
      <p class="sub" style="margin:8px 0 14px"><b style="color:var(--ink)">${esc(J.track.name)}</b> · ${J.done} of ${J.total} km${J.complete ? " · complete" : ` · next stop <b style="color:var(--ink)">${esc(J.next)}</b> in ${J.toNext} km`}</p>
      <div class="bar leaf"><i style="width:${pct}%"></i></div>
      <div class="stops">${J.track.stops.map(x => `<div class="stop ${J.done >= x.km ? "reached" : ""}">${landmark(x.key, 56)}<b>${esc(x.name)}</b><small>${x.km} km</small></div>`).join("")}</div>
      ${J.completed && J.completed.length ? `<p class="sub" style="margin:12px 0 0">Tracks finished: ${J.completed.map(c => `<b style="color:var(--ink)">${esc(c.name)}</b> (${c.km} km)`).join(", ")}</p>` : ""}</div>`;
  }

  S.awards = (s, d) => {
    const group = (t, sub, items) => `<div class="card"><div class="between"><h3>${t}</h3><span class="sub">${sub}</span></div><div class="medals">${items.map(m =>
      `<div class="medal ${m.got ? "" : "locked"}">${medalSvg(m.kind, m.label)}${esc(m.title)}<small>${esc(m.sub)}</small></div>`).join("")}</div></div>`;
    const body = `${journeyCard(s)}${group("Streak medals", "earned by showing up", s.medals.streak)}${group("Distance medals", "lifetime km", s.medals.distance)}${group("Special", "rare moments", s.medals.special)}`;
    if (d === "phone") return shell(d, "awards", s, body);
    return shell(d, "awards", s, `<div class="col">${body}</div><div class="col">${recordsCard(s)}</div>`);
  };

  /* ---------------- map + tracks ---------------- */
  function mapSvg(s) {
    const LM = window.WalkLandmarks && window.WalkLandmarks.map, J = s.journey, T = J.track;
    const proj = LM ? LM.project : (la, lo) => [10 + (lo - 34) * 0.917 * 49, 3 + (32.6 - la) * 49];
    const pts = T.stops.map(x => proj(x.lat, x.lon)), me = proj(J.pos.lat, J.pos.lon);
    // zoom to the track so city tracks (Riyadh, Jeddah) are readable; keep a sensible minimum window
    const xs = pts.map(p => p[0]).concat(me[0]), ys = pts.map(p => p[1]).concat(me[1]);
    const span = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys), 3);
    const pad = span * .35 + 2, w0 = Math.max(span + 2 * pad, 6);
    const cx = (Math.max(...xs) + Math.min(...xs)) / 2, cy = (Math.max(...ys) + Math.min(...ys)) / 2;
    const vw = Math.min(1000, w0 * 1.25), vh = Math.min(820, w0), z = vw / 1000;
    const vb = `${(cx - vw / 2).toFixed(2)} ${(cy - vh / 2).toFixed(2)} ${vw.toFixed(2)} ${vh.toFixed(2)}`;
    const P = p => `${p[0].toFixed(2)},${p[1].toFixed(2)}`;
    const line = pts.map((p, i) => `${i ? "L" : "M"}${P(p)}`).join("");
    const done = T.stops.filter(x => x.km <= J.done).map(x => proj(x.lat, x.lon)).concat([me]);
    const walked = done.map((p, i) => `${i ? "L" : "M"}${P(p)}`).join("");
    const sw = 9 * z, fs = 22 * z, r = 11 * z;
    const others = (J.places || []).filter(p => !T.stops.some(x => x.key === p.key)).map(p => { const q = proj(p.lat, p.lon);
      return `<circle cx="${q[0]}" cy="${q[1]}" r="${5 * z}" class="mapdot"><title>${esc(p.name)}</title></circle>`; }).join("");
    const stops = T.stops.map((x, i) => { const p = pts[i], left = i % 2 === 1, dy = (i % 4 < 2 ? -1 : 1) * fs * .2;
      return `<g class="mapstop ${J.done >= x.km ? "reached" : ""}"><circle cx="${p[0]}" cy="${p[1]}" r="${r}" style="stroke-width:${4 * z}"/>
        <text x="${p[0] + (left ? -1 : 1) * r * 1.6}" y="${p[1] + fs * .35 + dy}" text-anchor="${left ? "end" : "start"}" style="font-size:${fs}px;stroke-width:${6 * z}px">${esc(x.name)}</text></g>`; }).join("");
    const mw = 44 * z, mh = 48 * z;
    return `<svg class="mapsvg" viewBox="${vb}" role="img" aria-label="Map of Saudi Arabia with your track: ${esc(T.name)}">
      ${LM && LM.neighbors ? `<path d="${LM.neighbors}" class="mapnb" style="stroke-width:${z}"/>` : ""}${LM ? `<path d="${LM.saudi}" class="mapland" style="stroke-width:${2.5 * z}"/>` : ""}
      ${others}<path d="${line}" class="maproute" style="stroke-width:${sw};stroke-dasharray:${2 * z} ${14 * z}"/><path d="${walked}" class="mapwalked" style="stroke-width:${sw}"/>${stops}
      <svg x="${me[0] - mw / 2}" y="${me[1] - mh}" width="${mw}" height="${mh}" viewBox="0 0 120 130">${mascot("happy").replace(/^<svg[^>]*>/, "").replace(/<\/svg>$/, "")}</svg></svg>`;
  }
  S.map = (s, d) => {
    const J = s.journey, pick = s.customPick || J.custom || [];
    const trackCard = t => `<div class="trackcard ${t.id === J.track.id ? "on" : ""}">
        <div class="row" style="gap:4px">${t.stops.slice(0, 4).map(k => landmark(k, 34)).join("")}</div>
        <div style="flex:1;min-width:0"><b style="display:block">${esc(t.name)}</b><span class="sub">${t.total} km · ${esc(t.desc)}</span></div>
        ${t.id === J.track.id ? `<span class="tier done">Current</span>` : `<button class="btn mini" data-act="track" data-v="${t.id}">Start</button>`}</div>`;
    const custom = `<div class="card"><h3>Make your own track</h3><p class="sub" style="margin:-4px 0 12px">Tap places in the order you want to walk them (at least two). Distances are straight lines between landmarks.</p>
      <div class="placegrid">${J.places.map(p => { const i = pick.indexOf(p.key);
        return `<button class="placechip ${i >= 0 ? "on" : ""}" data-act="custompick" data-v="${p.key}">${landmark(p.key, 30)}<span class="pn">${esc(p.name)}</span>${i >= 0 ? `<i class="num">${i + 1}</i>` : ""}</button>`; }).join("")}</div>
      <div class="row" style="gap:10px;margin-top:14px;flex-wrap:wrap"><button class="btn" data-act="customstart" ${pick.length < 2 ? "disabled" : ""}>Start my track</button>${pick.length ? `<button class="btn ghost" data-act="customclear">Clear</button>` : ""}</div></div>`;
    const head = `<div class="card"><div class="between" style="flex-wrap:wrap;gap:10px"><div><span class="eyebrow">Walk across Saudi Arabia</span><h2 style="margin:4px 0 0;font-size:26px;font-weight:1000">${esc(J.track.name)}</h2>
        <span class="sub">${J.done} of ${J.total} km walked on this track${J.complete ? " · complete" : ` · ${J.toNext} km to ${esc(J.next)}`}</span></div>
        <button class="btn ghost" data-go="awards">Done</button></div>
      <div class="mapwrap">${mapSvg(s)}</div>
      <p class="sub" style="margin:8px 0 0">Your total distance on the pad moves you along the track. Switching track starts the new one from 0 km; your lifetime totals never change.</p></div>`;
    const list = `<div class="card"><h3>Choose a track</h3>${J.tracks.map(trackCard).join("")}</div>`;
    if (d === "phone") return shell(d, "awards", s, `${head}${list}${custom}`);
    return shell(d, "awards", s, `<div class="col">${head}${custom}</div><div class="col">${list}</div>`);
  };

  /* ---------------- goals editor ---------------- */
  S.goals = (s, d) => {
    const st = s.settings || { goals: [{ id: "g", metric: lm(s), period: "day", target: s.goal.goal, tiny: s.goal.tiny, stretch: s.goal.stretch, primary: true }],
      week_goal: s.weekGoal, month_goal: 12, cue: "start my first meeting of the day", nudge: { on: true, time: "16:00" }, modes: { ramadan: false, travel: false, sick: false } };
    const goals = st.goals, sg = s.suggestion || {};
    const seg = (id, act, cur, opts) => `<div class="segs">${opts.map(([v, l]) => `<button class="${v === cur ? "on" : ""}" data-act="${act}" data-id="${id}" data-v="${v}">${l}</button>`).join("")}</div>`;
    const numIn = (g, f, label) => `<div class="field"><label for="${g.id}-${f}">${label}</label>
      <div class="numin"><input id="${g.id}-${f}" class="input num" type="number" inputmode="decimal" min="0" step="${g.metric === "km" ? "0.1" : g.metric === "steps" ? "100" : "1"}" data-act="gfield" data-id="${g.id}" data-f="${f}" value="${g[f]}"><span>${UNIT[g.metric]}</span></div></div>`;
    const card = g => `<div class="card goalcard ${g.primary ? "main" : ""}">
        <div class="between" style="flex-wrap:wrap;gap:10px"><h3 style="margin:0">${g.primary ? `<span class="mainbadge">${I.flame}Main goal</span>` : ""}${esc(MNAME[g.metric])}, ${g.period === "day" ? "every day" : "every week"}</h3>
          <div class="row" style="gap:8px">${!g.primary && g.period === "day" ? `<button class="btn ghost mini" data-act="gprimary" data-id="${g.id}">${I.star}Make main</button>` : ""}
          ${goals.length > 1 ? `<button class="btn ghost mini danger" data-act="gdel" data-id="${g.id}" aria-label="Delete goal">${I.trash}</button>` : ""}</div></div>
        <div class="goalgrid">
          <div class="field wide"><label>Measure</label>${seg(g.id, "gmetric", g.metric, [["steps", "Pad steps"], ["allsteps", "All day"], ["minutes", "Minutes"], ["km", "Km"]])}
            ${g.metric === "allsteps" ? `<span class="help">${s.health && s.health.connected ? "From Apple Health: phone, watch and pad together." : "Needs Apple Health (see Phone and Apple Health). Until then it counts pad steps."}</span>` : ""}</div>
          <div class="field"><label>Period</label>${seg(g.id, "gperiod", g.period, [["day", "Daily"], ["week", "Weekly"]])}</div>
          ${numIn(g, "target", g.period === "day" ? "Goal" : "Goal per week")}
          ${g.period === "day" ? numIn(g, "tiny", g.primary ? "Tiny (keeps your streak)" : "Tiny") + numIn(g, "stretch", "Stretch (bonus)") : ""}
        </div>
        ${g.primary ? `<p class="sub" style="margin:10px 0 0">Your main goal fills the ring, decides goal days and drives your streak.</p>` : ""}</div>`;
    const sugBanner = sg.target && sg.target !== goals.find(g => g.primary)?.target
      ? `<div class="banner sky">${I.bolt}<div><b>Suggestion: ${fu(sg.metric, sg.target)} a day</b>${esc(sg.why)}<div style="margin-top:10px"><button class="btn sky mini" data-act="gsugg" data-v="${sg.target}">Use ${fu(sg.metric, sg.target)}</button></div></div></div>`
      : sg.why ? `<div class="banner sky">${I.bolt}<div><b>Keep your main goal for now</b>${esc(sg.why)}</div></div>` : "";
    const sw = (path, on) => `<button class="switch ${on ? "on" : ""}" data-act="toggle" data-k="${path}" aria-pressed="${on}" aria-label="toggle"></button>`;
    const opt = (k, v, label, on) => `<button class="opt ${on ? "on" : ""}" data-act="set" data-k="${k}" data-v="${v}"><b class="num">${v}</b><span>${label}</span></button>`;
    const t12 = t => { const [h, m] = t.split(":").map(Number); return `${(h % 12) || 12}:${String(m).padStart(2, "0")} ${h < 12 ? "am" : "pm"}`; };
    const body = `
      <div class="between" style="flex-wrap:wrap;gap:10px"><div><h2 style="margin:0;font-size:28px;font-weight:1000">Your goals</h2><span class="sub">Set any number. Steps, minutes or kilometres, daily or weekly.</span></div>
        <button class="btn" data-act="gadd" ${goals.length >= 8 ? "disabled" : ""}>${I.plus}Add a goal</button></div>
      ${sugBanner}${goals.map(card).join("")}
      <div class="card"><h3>Week and month</h3>
        <div class="field"><label>Goal days per week</label><div class="seg four" style="grid-template-columns:repeat(4,minmax(0,1fr))">${[3, 4, 5, 6].map(v => opt("week_goal", v, v === 5 ? "suggested" : "days", v === st.week_goal)).join("")}</div><span class="help">A goal day = your main goal reached. The week runs Sunday to Saturday.</span></div>
        <div class="field" style="margin-top:14px"><label>Monthly challenge</label><div class="seg">${[8, 12, 16].map(v => opt("month_goal", v, "goal days", v === st.month_goal)).join("")}</div></div></div>
      <div class="card"><h3>Your walking cue</h3>
        <div class="field"><label for="cue">After I…</label><input id="cue" class="input" data-act="cue" value="${esc(st.cue)}" maxlength="120"><span class="help">…I step on the pad. Pairing a walk with something you already do makes it automatic.</span></div>
        <div class="li" style="margin-top:10px"><span class="ic" style="background:var(--sky-l);color:var(--sky-d)">${I.bell}</span><div><b>One gentle nudge</b><span class="sub">At <input type="time" class="input" data-act="nudgetime" value="${esc(st.nudge.time)}" style="padding:2px 6px;width:auto"> (${t12(st.nudge.time)}), only if you haven't walked yet</span></div><span style="margin-left:auto">${sw("nudge.on", st.nudge.on)}</span></div></div>
      ${linkCard(s)}
      <div class="card"><h3>Pause modes</h3><p class="sub" style="margin:-4px 0 6px">Your streak and week are paused, never broken.</p>
        ${[["moon", "ramadan", "Ramadan", "Daily goals −40% while on"], ["plane", "travel", "Travelling", "Days don't count against you"], ["bed", "sick", "Unwell", "Rest. No goals, no nudges"]].map(([ic, k, t, sub]) =>
        `<div class="li"><span class="ic" style="background:var(--berry-l);color:var(--berry)">${I[ic]}</span><div><b>${t}</b><span class="sub">${sub}</span></div><span style="margin-left:auto">${sw("modes." + k, st.modes[k])}</span></div>`).join("")}</div>`;
    if (d === "phone") return shell(d, "goals", s, body);
    return shell(d, "goals", s, `<div class="col">${body}</div><div class="col">${goalsCard(s)}<div class="card"><h3>How goals work</h3>
      <div class="li"><span class="ic" style="background:var(--flame-l);color:var(--flame-d)">${I.flame}</span><div><b>One main goal</b><span class="sub">It fills the ring and decides goal days. Its tiny level keeps your streak.</span></div></div>
      <div class="li"><span class="ic" style="background:var(--leaf-l);color:var(--leaf-d)">${I.check}</span><div><b>Extra goals</b><span class="sub">Track anything else, daily or weekly, without touching your streak.</span></div></div>
      <div class="li"><span class="ic" style="background:var(--sky-l);color:var(--sky-d)">${I.gear}</span><div><b>Every number is yours</b><span class="sub">Change anything, any time. Past days keep the goal they had.</span></div></div></div></div>`);
  };

  S.onboard = (s, d) => {
    const ob = s.onboard || { typical: 2700, metric: "steps", options: [1500, 2500, 3750] };
    const metric = s.pickMetric || "steps";
    const opts = metric === "steps" ? ob.options : [20, 30, 45];
    const pick = s.pick && opts.includes(s.pick) ? s.pick : opts[1];
    const opt = (v, l) => `<button class="opt ${v === pick ? "on" : ""}" data-act="pick" data-v="${v}"><b class="num">${fv(metric, v)}</b><span>${UNIT[metric]} · ${l}</span></button>`;
    const inner = `<div style="display:grid;gap:22px;justify-items:center;text-align:center;max-width:580px;margin:0 auto;padding:${d === "phone" ? "28px 18px" : "60px 20px"}">
      ${mascot("happy").replace('class="mascot"', 'style="width:150px;height:150px"')}
      <div><span class="eyebrow">Welcome</span><h2 style="margin:6px 0;font-size:${d === "phone" ? 26 : 34}px;font-weight:1000;letter-spacing:-.02em">What's your daily walking goal?</h2>
      <p class="sub" style="margin:0">${metric === "steps" && ob.typical ? `From your walks so far, a typical walking day was <b style="color:var(--ink)">${n(ob.typical)} steps</b>. We suggest starting a little below that.` : "Start small. You can add more goals and change them any time."}</p></div>
      <div class="segs" style="width:100%">${[["steps", "Steps"], ["minutes", "Minutes"]].map(([k, l]) => `<button class="${k === metric ? "on" : ""}" data-act="pickmetric" data-v="${k}">${l}</button>`).join("")}</div>
      <div class="seg" style="width:100%">${opt(opts[0], "easy start")}${opt(opts[1], "suggested")}${opt(opts[2], "ambitious")}</div>
      <div class="banner" style="background:var(--leaf-l);color:var(--leaf-d);text-align:left;width:100%">${I.flame}<div><b>Your streak only needs a tiny walk.</b>Busy day? ${metric === "steps" ? "500 steps" : "5 minutes"} on the pad keeps it alive. The goal is a separate ring.</div></div>
      <button class="btn wide" data-act="onboard" data-metric="${metric}" data-v="${pick}">Start walking</button></div>`;
    return `<div class="app ${d}" style="${d === "desktop" ? "grid-template-columns:1fr" : "grid-template-rows:1fr"};align-content:center">${inner}</div>`;
  };

  /* ---------------- community ---------------- */
  const initials = name => esc((name || "?").trim().split(/\s+/).map(w => w[0]).slice(0, 2).join("").toUpperCase());
  const COLORS = ["#3FBF4A", "#FF8A1F", "#22A6F2", "#9B6BFF", "#FFC52E", "#FF5C8A"];
  const avatar = (name, size = 40) => { let h = 0; for (const c of name || "") h = (h * 31 + c.charCodeAt(0)) >>> 0;
    return `<span class="avatar" style="width:${size}px;height:${size}px;background:${COLORS[h % COLORS.length]}">${initials(name)}</span>`; };

  S.community = (s, d) => {
    const C = s.community || {}, X = s.cdata || {};
    const err = s.cerror ? `<div class="banner flame">${I.bolt}<div><b>That didn't work</b>${esc(s.cerror)}</div></div>` : "";
    if (!C.enabled) {
      const join = `${err}<div class="card" style="display:grid;gap:16px;justify-items:center;text-align:center">
          <div class="row" style="gap:0">${["Noura A", "Faisal K", "You", "Lama S"].map((x, i) => `<span style="margin-left:${i ? -12 : 0}px">${avatar(x, 54)}</span>`).join("")}</div>
          <div><h2 style="margin:0;font-size:28px;font-weight:1000">Join the walking pad community</h2>
          <p class="sub" style="margin:6px auto 0;max-width:52ch">Walk with friends and colleagues anywhere. Make a group, share its invite code, and see who's walking the most this week.</p></div></div>
        <div class="card"><h3>Pick your user ID</h3>
          <div class="goalgrid">
            <div class="field"><label for="chandle">User ID</label><div class="numin"><span>@</span><input id="chandle" class="input" data-cin="handle" maxlength="20" placeholder="e.g. mohammed_walks" value="${esc(s.cform?.handle || "")}" autocomplete="off"></div><span class="help">3–20 letters, numbers or _ . Friends find you with it.</span></div>
            <div class="field"><label for="cname">Display name</label><input id="cname" class="input" data-cin="display_name" maxlength="40" placeholder="Your name" value="${esc(s.cform?.display_name || "")}"><span class="help">Shown on leaderboards.</span></div>
          </div>
          <div class="li" style="margin-top:6px"><span class="ic" style="background:var(--sun-l);color:var(--sun-d)">${I.crown}</span><div><b>Show me on the global leaderboard</b><span class="sub">Off = only your groups see you.</span></div><span style="margin-left:auto"><button class="switch ${s.cform?.public ? "on" : ""}" data-act="cformpublic" aria-label="toggle"></button></span></div>
          <button class="btn wide" data-act="cjoin" style="margin-top:16px">Join the community</button></div>
        <div class="card"><h3>What gets shared</h3>
          <div class="li"><span class="ic" style="background:var(--leaf-l);color:var(--leaf-d)">${I.check}</span><div><b>Daily totals only</b><span class="sub">Steps, minutes, km, whether you hit your goal, and your streak.</span></div></div>
          <div class="li"><span class="ic" style="background:var(--berry-l);color:var(--berry)">${I.shield}</span><div><b>Never shared</b><span class="sub">Your walks second by second, times of day, location, or anything about your PC.</span></div></div>
          <div class="li"><span class="ic" style="background:var(--sky-l);color:var(--sky-d)">${I.trash}</span><div><b>Leave any time</b><span class="sub">Leaving deletes your community data from the server.</span></div></div></div>`;
      return d === "phone" ? shell(d, "community", s, join) : shell(d, "community", s, `<div class="col">${join}</div><div class="col"></div>`);
    }
    const me = X.me || {}, groups = me.groups || [], board = X.board || { rows: [] }, q = s.cq || {};
    const scopes = [["global", "Everyone"]].concat(groups.map(g => ["group:" + g.group_id, g.name]));
    const tab = (act, v, l, on) => `<button class="tier ${on ? "next" : ""}" data-act="${act}" data-v="${esc(v)}">${esc(l)}</button>`;
    const metricLabel = { steps: "steps", minutes: "min", km: "km", goal_days: "goal days", streak: "day streak" }[q.metric || "steps"];
    const fmtB = v => q.metric === "km" ? (+v).toFixed(1) : (+v).toLocaleString("en-US", { maximumFractionDigits: 0 });
    const rows = board.rows || [];
    const lb = `<div class="card"><div class="between" style="flex-wrap:wrap;gap:8px"><h3 style="margin:0">Leaderboard</h3>
        <div class="row" style="gap:6px;flex-wrap:wrap">${tab("lperiod", "week", "This week", (q.period || "week") === "week")}${tab("lperiod", "month", "This month", q.period === "month")}</div></div>
      <div class="row" style="gap:6px;flex-wrap:wrap;margin:12px 0">${scopes.map(([v, l]) => tab("lscope", v, l, (q.scope || "global") === v)).join("")}</div>
      <div class="row" style="gap:6px;flex-wrap:wrap;margin-bottom:8px">${[["steps", "Steps"], ["minutes", "Minutes"], ["km", "Km"], ["goal_days", "Goal days"], ["streak", "Streak"]].map(([v, l]) => tab("lmetric", v, l, (q.metric || "steps") === v)).join("")}</div>
      ${X.loading ? `<p class="sub">Loading…</p>` : rows.length ? rows.map(r => `<div class="lbrow ${r.me ? "me" : ""}"><span class="rank num ${r.rank <= 3 ? "top" + r.rank : ""}">${r.rank}</span>${avatar(r.display_name)}<div style="min-width:0"><b>${esc(r.display_name)}${r.me ? " (you)" : ""}</b><span class="sub">@${esc(r.handle)}</span></div><span class="end num">${fmtB(r.value)} <small>${metricLabel}</small></span></div>`).join("")
        : `<p class="sub">${(q.scope || "global") === "global" ? "No one on the global board yet for this period. Make a group and invite people." : "No walks in this group for this period yet."}</p>`}
      ${board.me && !rows.some(r => r.me) ? `<div class="lbrow me" style="margin-top:8px"><span class="rank num">${board.me.rank ?? "–"}</span>${avatar(me.display_name)}<div><b>You</b><span class="sub">${C.public || (q.scope || "global") !== "global" ? "" : "private: only you see this row"}</span></div><span class="end num">${fmtB(board.me.value)} <small>${metricLabel}</small></span></div>` : ""}</div>`;
    const prof = `<div class="card"><div class="row">${avatar(me.display_name || C.display_name, 56)}<div style="min-width:0"><b style="display:block;font-size:19px">${esc(me.display_name || C.display_name)}</b>
        <span class="sub">@${esc(C.handle)} · user ID <b class="num" style="color:var(--ink)">${esc(C.user_id || "")}</b></span></div>
        <button class="btn ghost mini" data-act="copy" data-v="@${esc(C.handle)}" style="margin-left:auto">${I.copy}Copy</button></div>
      <p class="sub" style="margin:10px 0 0">${C.last_sync ? `Last synced ${esc(C.last_sync.replace("T", " ").slice(0, 16))}` : "Not synced yet"} · <a data-act="csync" style="color:var(--sky-d);cursor:pointer">Sync now</a></p></div>`;
    const gl = `<div class="card"><h3>Your groups</h3>
      ${groups.length ? groups.map(g => `<div class="li"><span class="ic" style="background:var(--leaf-l);color:var(--leaf-d)">${I.users}</span><div style="min-width:0"><b>${esc(g.name)}</b><span class="sub">${g.members} member${g.members === 1 ? "" : "s"} · code <b class="num" style="color:var(--ink)">${esc(g.invite_code)}</b>${g.role === "owner" ? " · you made it" : ""}</span></div>
        <div class="row" style="gap:6px;margin-left:auto"><button class="btn ghost mini" data-act="copy" data-v="${esc(g.invite_code)}" aria-label="Copy invite code">${I.copy}</button><button class="btn ghost mini danger" data-act="gleave" data-v="${esc(g.group_id)}">Leave</button></div></div>`).join("")
        : `<p class="sub" style="margin:0">No groups yet. Make one for your team or family, or join with a code.</p>`}
      <div class="goalgrid" style="margin-top:14px">
        <div class="field"><label for="gname">New group</label><div class="row" style="gap:8px"><input id="gname" class="input" data-cin="group_name" maxlength="40" placeholder="e.g. DCSI walkers" value="${esc(s.cform?.group_name || "")}"><button class="btn mini" data-act="gcreate">${I.plus}Create</button></div></div>
        <div class="field"><label for="gcode">Join with a code</label><div class="row" style="gap:8px"><input id="gcode" class="input num" data-cin="invite_code" maxlength="12" placeholder="8-letter code" value="${esc(s.cform?.invite_code || "")}"><button class="btn sky mini" data-act="gjoin">Join</button></div></div>
      </div></div>`;
    const settings = `<div class="card"><h3>Privacy</h3>
      <div class="li"><span class="ic" style="background:var(--sun-l);color:var(--sun-d)">${I.crown}</span><div><b>Show me on the global leaderboard</b><span class="sub">Your groups always see you.</span></div><span style="margin-left:auto"><button class="switch ${C.public ? "on" : ""}" data-act="cpublic" aria-label="toggle"></button></span></div>
      <div class="li"><span class="ic" style="background:var(--flame-l);color:var(--flame-d)">${I.trash}</span><div><b>Leave the community</b><span class="sub">Deletes your user ID and shared totals from the server.</span></div><button class="btn ghost mini danger" data-act="cleave" style="margin-left:auto">Leave</button></div></div>`;
    if (d === "phone") return shell(d, "community", s, `${err}${prof}${lb}${gl}${settings}`);
    return shell(d, "community", s, `<div class="col">${err}${lb}</div><div class="col">${prof}${gl}${settings}</div>`);
  };


  /* ---------------- phone link + Apple Health ---------------- */
  function linkCard(s) {
    if (s.remote) {
      return `<div class="card"><h3>Phone and Apple Health</h3>
        <div class="li"><span class="ic" style="background:var(--leaf-l);color:var(--leaf-d)">${I.check}</span><div><b>This phone is linked to your PC</b><span class="sub">Changes here reach your PC within a few seconds.</span></div></div>
        <div class="li"><span class="ic" style="background:#FFE3EA;color:#E0245E">${I.drop}</span><div><b>Apple Health</b><span class="sub">${s.health && s.health.connected ? `Connected · last steps ${esc(s.health.lastDate)}` : "Write pad walks to Health and read your all-day steps."}</span></div><button class="btn mini" data-go="health" style="margin-left:auto">Set up</button></div>
        <div class="li"><span class="ic" style="background:var(--flame-l);color:var(--flame-d)">${I.trash}</span><div><b>Unlink this phone</b><span class="sub">You can link it again with a new code.</span></div><button class="btn ghost mini danger" data-act="unlink" style="margin-left:auto">Unlink</button></div></div>`;
    }
    const C = s.community || {}, P = s.pairInfo;
    if (!C.enabled) return `<div class="card"><h3>Use it on your phone</h3><p class="sub" style="margin:0">Create your account first (Community tab). It stays private unless you choose otherwise; then you can link your phone and Apple Health.</p>
      <button class="btn ghost mini" data-go="community" style="margin-top:12px">Create my account</button></div>`;
    const devs = (s.devices || []).map(d => `<div class="li"><span class="ic" style="background:var(--sky-l);color:var(--sky-d)">${I.users}</span><div><b>${esc(d.label)}</b><span class="sub">linked ${esc((d.created_at || "").slice(0, 10))}${d.last_seen ? ` · seen ${esc(d.last_seen.slice(0, 16).replace("T", " "))}` : ""}</span></div><button class="btn ghost mini danger" data-act="revoke" data-v="${esc(d.id)}" style="margin-left:auto">Unlink</button></div>`).join("");
    return `<div class="card"><h3>Use it on your phone</h3>
      <p class="sub" style="margin:-4px 0 12px">Your phone shows everything live from this PC and can change goals, tracks and the pad. Apple Health is set up from the phone.</p>
      ${P ? `<div class="paircode"><span class="sub">On your phone, open</span><b class="num">${esc(P.url)}</b><span class="sub">and enter this code (10 minutes):</span><div class="code num">${esc(P.code)}</div></div>`
          : `<button class="btn" data-act="pair">${I.plus}Link a phone</button>`}
      ${devs ? `<div style="margin-top:12px">${devs}</div>` : ""}</div>`;
  }

  S.pair = (s, d) => `<div class="app ${d}" style="${d === "desktop" ? "grid-template-columns:1fr" : "grid-template-rows:1fr"};align-content:center">
    <div style="display:grid;gap:18px;justify-items:center;text-align:center;max-width:460px;margin:0 auto;padding:32px 18px">
      ${mascot("happy").replace('class="mascot"', 'style="width:130px;height:130px"')}
      <div><span class="eyebrow">Walking Pad</span><h2 style="margin:6px 0;font-size:28px;font-weight:1000">Link this phone to your PC</h2>
      <p class="sub" style="margin:0">On your PC, open Walking Pad → Goals → <b style="color:var(--ink)">Link a phone</b>, then type the code here.</p></div>
      ${s.perror ? `<div class="banner flame" style="width:100%;text-align:left">${I.bolt}<div><b>That didn't work</b>${esc(s.perror)}</div></div>` : ""}
      <div class="field" style="width:100%;text-align:left"><label for="pcode">Code from your PC</label><input id="pcode" class="input num paircodein" data-pin="code" maxlength="6" autocomplete="one-time-code" autocapitalize="characters" placeholder="ABC123" value="${esc(s.pform?.code || "")}"></div>
      <div class="field" style="width:100%;text-align:left"><label for="pname">Name this device</label><input id="pname" class="input" data-pin="label" maxlength="40" value="${esc(s.pform?.label || "iPhone")}"></div>
      <button class="btn wide" data-act="claim">Link</button></div></div>`;

  S.waiting = (s, d) => `<div class="app ${d}" style="${d === "desktop" ? "grid-template-columns:1fr" : "grid-template-rows:1fr"};align-content:center">
    <div class="boot">${mascot("sleepy").replace('class="mascot"', 'style="width:120px;height:120px"')}<b style="font-size:22px">Waiting for your PC</b>
    <span class="sub" style="max-width:40ch">Linked. As soon as Walking Pad on your PC sends its first update, everything shows up here.</span></div></div>`;

  S.health = (s, d) => {
    const base = s.remote ? s.remote.base : "", tok = s.remote ? s.remote.token : "";
    const copy = (label, v) => `<div class="copyrow"><span class="sub">${label}</span><code>${esc(v)}</code><button class="btn ghost mini" data-act="copy" data-v="${esc(v)}">${I.copy}Copy</button></div>`;
    const step = (n, t, body) => `<li><b>${n}. ${t}</b><div class="sub">${body}</div></li>`;
    const body = `<div class="card"><div class="between"><div><span class="eyebrow">Apple Health</span><h2 style="margin:4px 0 0;font-size:26px;font-weight:1000">Sync with Apple Health</h2></div><button class="btn ghost" data-go="goals">Done</button></div>
      <p class="sub" style="margin:10px 0 0">Apple only lets native iPhone apps touch Health directly, so we use the built-in <b style="color:var(--ink)">Shortcuts</b> app. You build two small shortcuts once, then iPhone runs them for you. Your token below is private to this phone: anyone with it can see your walks.</p></div>
    <div class="card"><h3>Values you'll paste</h3>${copy("Write URL", base + "/v1/health/export")}${copy("Done URL", base + "/v1/health/ack")}${copy("Read URL", base + "/v1/health/import")}${copy("Header value", "Bearer " + tok)}</div>
    <div class="card"><h3>Shortcut 1 · Pad walks → Apple Health</h3><ol class="steps">
      ${step(1, "Get Contents of URL", "Paste the <b>Write URL</b>. Show more → Headers → add <code>Authorization</code> with the <b>Header value</b>.")}
      ${step(2, "Get Dictionary Value", "Key <code>items</code> from Contents of URL.")}
      ${step(3, "Repeat with Each", "item in Dictionary Value. Inside the repeat:")}
      ${step(4, "Get Dictionary Value ×4", "Keys <code>steps</code>, <code>km</code>, <code>start</code>, <code>end</code> from Repeat Item.")}
      ${step(5, "Log Health Sample: Steps", "Value = steps. Start Date = start, End Date = end (tap the date field and choose the variable).")}
      ${step(6, "Log Health Sample: Walking + Running Distance", "Value = km, unit km, same start and end.")}
      ${step(7, "After the repeat: Get Dictionary Value", "Key <code>ids</code> from Contents of URL (step 1).")}
      ${step(8, "Get Contents of URL", "Paste the <b>Done URL</b>. Method POST, same Authorization header, Request Body JSON with field <code>ids</code> = Dictionary Value.")}
    </ol><p class="sub">Step 8 marks walks as written, so they are never added twice.</p></div>
    <div class="card"><h3>Shortcut 2 · Apple Health → Walking Pad</h3><ol class="steps">
      ${step(1, "Find Health Samples", "Type Steps, Start Date is Today, Group By Day. This gives Health's own daily total, without double counting.")}
      ${step(2, "Calculate Statistics", "Sum of Health Samples.")}
      ${step(3, "Format Date", "Current Date, custom format <code>yyyy-MM-dd</code>.")}
      ${step(4, "Get Contents of URL", "Paste the <b>Read URL</b>. Method POST, same Authorization header, Request Body JSON: <code>date</code> = Formatted Date, <code>steps</code> = Statistics.")}
    </ol></div>
    <div class="card"><h3>Make them run by themselves</h3>
      <p class="sub" style="margin:0">Shortcuts → Automation → <b style="color:var(--ink)">+</b> → Time of Day (for example every evening at 21:00, and a second one at 13:00) → Run Immediately → choose the shortcut. Add one automation per shortcut.</p>
      ${s.health && s.health.connected ? `<div class="banner sky" style="margin-top:12px">${I.check}<div><b>Working</b>Last steps from Health: ${esc(s.health.lastDate)}${s.health.today != null ? ` · today ${n(s.health.today)} steps` : ""}.</div></div>` : ""}
      <p class="sub" style="margin:12px 0 0">Then add a goal on <b style="color:var(--ink)">All-day steps</b> in Goals to use your Health total.</p></div>`;
    return shell(d, "goals", s, d === "phone" ? body : `<div class="col">${body}</div><div class="col"></div>`);
  };

  W.WalkUI = { I, mascot, medalSvg, S, ring, esc, n, km, mmss, fv, fu, landmark };
})(window);
