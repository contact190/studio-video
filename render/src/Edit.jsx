import React from 'react';
import {AbsoluteFill, Sequence, Loop, OffthreadVideo, Audio, Img, staticFile, useCurrentFrame, useVideoConfig, interpolate, spring} from 'remotion';

const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};
const up = (t, c) => (c === 'upper' ? String(t).toUpperCase() : c === 'lower' ? String(t).toLowerCase() : t);

const Check = ({size, color}) => (
  <svg width={size} height={size} viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" /></svg>
);

// ---------------------------------------------------------------- image
const Clip = ({c, img, broll}) => {
  const f = useCurrentFrame();
  const amt = img.zoom_amount ?? 0.04;
  const z = img.zoom === 'slow_in' ? 1 + amt * (f / Math.max(1, c.dur)) : img.zoom === 'punch' ? 1 + amt * Math.max(0, 1 - f / 8) : 1;
  const sat = c.speaker && img.saturation_speaker != null ? img.saturation_speaker : (img.saturation ?? 1);
  const warm = img.warm ? ` sepia(${img.warm}) hue-rotate(-8deg)` : '';
  const filter = `contrast(${img.contrast || 1}) saturate(${sat}) brightness(${img.brightness || 1})${warm}`;
  const vid = (extra) => <OffthreadVideo src={staticFile(c.src)} volume={c.volume} style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${z})`, filter, ...extra}} />;
  if (img.layout === 'split' && c.speaker && broll) {
    return (
      <AbsoluteFill style={{background: '#000'}}>
        <div style={{position: 'absolute', top: 0, left: 0, right: 0, height: '50%', overflow: 'hidden'}}>{vid({objectPosition: '50% 30%'})}</div>
        <div style={{position: 'absolute', bottom: 0, left: 0, right: 0, height: '50%', overflow: 'hidden', borderTop: '4px solid #000'}}>
          <Loop durationInFrames={broll.dur}><OffthreadVideo src={staticFile(broll.src)} muted style={{width: '100%', height: '100%', objectFit: 'cover', filter}} /></Loop>
        </div>
      </AbsoluteFill>
    );
  }
  if (img.frame === 'square' && c.speaker) {
    return (
      <AbsoluteFill style={{background: '#111', overflow: 'hidden'}}>
        <OffthreadVideo src={staticFile(c.src)} muted style={{width: '100%', height: '100%', objectFit: 'cover', filter: `blur(40px) brightness(0.45) ${filter}`, transform: 'scale(1.2)'}} />
        <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
          <div style={{width: '88%', aspectRatio: '1 / 1', borderRadius: 28, overflow: 'hidden', boxShadow: '0 24px 70px rgba(0,0,0,0.6)'}}>{vid({})}</div>
        </AbsoluteFill>
      </AbsoluteFill>
    );
  }
  return <AbsoluteFill style={{overflow: 'hidden', background: '#000'}}>{vid({})}</AbsoluteFill>;
};

// ---------------------------------------------------------------- incrustations
const Stars = ({size}) => <span style={{color: '#FFC531', fontSize: size, letterSpacing: size * 0.08}}>★★★★★</span>;

const Overlay = ({o, W, H, accent}) => {
  const f = useCurrentFrame();
  const len = o.to - o.from;
  const p = spring({frame: f, fps: 30, config: {damping: 14, stiffness: 200}});
  const out = interpolate(f, [len - 6, len], [1, 0], CL);
  if (o.type === 'card') {
    return (
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', background: `rgba(0,0,0,${0.55 * out})`}}>
        <div style={{fontFamily: 'Inter', fontWeight: 900, color: '#fff', fontSize: W * (o.text.length <= 3 ? 0.32 : o.text.length <= 8 ? 0.13 : 0.075),
          textAlign: 'center', padding: `0 ${W * 0.08}px`, lineHeight: 1.05, letterSpacing: -1, opacity: p * out, transform: `scale(${0.7 + 0.3 * p})`,
          textShadow: '0 8px 30px rgba(0,0,0,0.6)'}}>{o.text.length <= 8 ? String(o.text).toUpperCase() : o.text}</div>
      </AbsoluteFill>
    );
  }
  if (o.type === 'stat') {
    const v = o.value * interpolate(f, [0, 18], [0, 1], {...CL, easing: (t) => 1 - Math.pow(1 - t, 3)});
    const shown = Number.isInteger(o.value) ? Math.round(v) : v.toFixed(1);
    return (
      <div style={{position: 'absolute', left: 0, right: 0, top: H * 0.3, textAlign: 'center', fontFamily: 'Inter', color: '#fff', opacity: p * out,
        transform: `scale(${0.8 + 0.2 * p})`, textShadow: '0 10px 40px rgba(0,0,0,0.7)'}}>
        <div style={{fontSize: W * 0.26, fontWeight: 900, letterSpacing: -4, lineHeight: 1, color: accent}}>{shown}{o.suffix}</div>
        {o.label ? <div style={{fontSize: W * 0.05, fontWeight: 800, marginTop: W * 0.01}}>{up(o.label, 'upper')}</div> : null}
      </div>
    );
  }
  if (o.type === 'name') {
    return (
      <div style={{position: 'absolute', left: W * 0.06, top: H * 0.62, opacity: p * out, transform: `translateX(${(1 - p) * -60}px)`, fontFamily: 'Inter'}}>
        <div style={{display: 'inline-block', background: '#fff', color: '#111', padding: `${W * 0.012}px ${W * 0.03}px`, fontSize: W * 0.05, fontWeight: 900, borderRadius: W * 0.01}}>{o.text}</div>
        <div style={{display: 'block', marginTop: W * 0.008}}>
          <span style={{display: 'inline-block', background: accent, color: '#fff', padding: `${W * 0.006}px ${W * 0.02}px`, fontSize: W * 0.03, fontWeight: 700, borderRadius: W * 0.008}}>{o.sub}</span>
        </div>
      </div>
    );
  }
  if (o.type === 'review') {
    return (
      <div style={{position: 'absolute', left: W * 0.07, right: W * 0.07, top: H * 0.09, opacity: p * out, transform: `translateY(${(1 - p) * -30}px)`}}>
        <div style={{background: 'rgba(255,255,255,0.96)', borderRadius: W * 0.03, padding: `${W * 0.03}px ${W * 0.04}px`, fontFamily: 'Inter', boxShadow: '0 16px 50px rgba(0,0,0,0.4)'}}>
          <Stars size={W * 0.05} />
          <div style={{fontSize: W * 0.042, fontWeight: 800, color: '#111', marginTop: W * 0.012, lineHeight: 1.2}}>“{o.text}”</div>
          <div style={{fontSize: W * 0.026, fontWeight: 600, color: '#2e9e5b', marginTop: W * 0.012}}>✓ Verified buyer</div>
        </div>
      </div>
    );
  }
  return null;
};

// ---------------------------------------------------------------- textes
const Hook = ({hook, st, W, H}) => {
  const f = useCurrentFrame();
  const p = spring({frame: f, fps: 30, config: {damping: 14, stiffness: 180}});
  const out = interpolate(f, [hook.to - hook.from - 6, hook.to - hook.from], [1, 0], CL);
  return (
    <div style={{position: 'absolute', left: 0, right: 0, top: st.position_y * H, display: 'flex', justifyContent: 'center', opacity: out}}>
      <div style={{maxWidth: W * 0.86, padding: `${W * 0.018}px ${W * 0.035}px`, background: st.bg, color: st.color, borderRadius: W * (st.radius || 0.01),
        fontFamily: 'Inter', fontWeight: st.weight || 900, fontSize: W * st.size, lineHeight: 1.08, textAlign: 'center', letterSpacing: -0.5,
        transform: `scale(${0.8 + 0.2 * p})`, opacity: p, boxShadow: '0 12px 40px rgba(0,0,0,0.35)'}}>
        {up(hook.text, st.case)}
      </div>
    </div>
  );
};

const Subtitles = ({subs, st, W, H}) => {
  const f = useCurrentFrame();
  const s = subs.find((x) => f >= x.from && f < x.to);
  if (!s || !st.enabled) return null;
  const p = st.animation === 'pop' || st.mode === 'bubble' ? spring({frame: f - s.from, fps: 30, config: {damping: 12, stiffness: 260, mass: 0.6}}) : 1;
  const words = s.words;
  const lines = words.length > 2 ? [words.slice(0, Math.ceil(words.length / 2)), words.slice(Math.ceil(words.length / 2))] : [words];
  let k = -1;
  if (st.mode === 'bubble') {
    return (
      <div style={{position: 'absolute', left: W * 0.08, right: W * 0.08, top: st.position_y * H, display: 'flex', justifyContent: (s.from / 30) % 2 < 1 ? 'flex-start' : 'flex-end'}}>
        <div style={{maxWidth: W * 0.72, background: st.bubble_bg || '#fff', color: st.bubble_color || '#111', fontFamily: 'Inter', fontWeight: 600,
          fontSize: W * st.size, lineHeight: 1.25, padding: `${W * 0.022}px ${W * 0.035}px`, borderRadius: W * 0.045, boxShadow: '0 10px 30px rgba(0,0,0,0.35)',
          transform: `translateY(${(1 - p) * 20}px) scale(${0.9 + 0.1 * p})`, transformOrigin: 'bottom left'}}>
          {words.map((w, i) => <span key={i} style={{color: i === s.hi ? st.highlight_color : undefined, fontWeight: i === s.hi ? 800 : 600}}>{w} </span>)}
        </div>
      </div>
    );
  }
  return (
    <div style={{position: 'absolute', left: W * 0.06, right: W * 0.06, top: st.position_y * H, textAlign: 'center',
      transform: `translateY(-50%) scale(${0.85 + 0.15 * p})`, fontFamily: st.font || 'Inter', fontWeight: st.weight || 900,
      fontSize: W * st.size, lineHeight: 1.04, letterSpacing: `${st.letter_spacing || 0}em`, textShadow: st.shadow}}>
      {lines.map((ln, i) => (
        <div key={i}>
          {ln.map((w) => { k += 1; return <span key={k} style={{color: k === s.hi ? st.highlight_color : st.color}}>{up(w, st.case)}{' '}</span>; })}
        </div>
      ))}
    </div>
  );
};

const Tag = ({t, st, W, H}) => {
  const f = useCurrentFrame();
  const p = spring({frame: f, fps: 30, config: {damping: 14, stiffness: 200}});
  return (
    <div style={{position: 'absolute', left: 0, right: 0, top: st.position_y * H, display: 'flex', justifyContent: 'center', opacity: p, transform: `translateY(${(1 - p) * 20}px)`}}>
      <div style={{display: 'flex', alignItems: 'center', gap: W * 0.018, padding: `${W * 0.012}px ${W * 0.024}px`, background: st.bg,
        border: `2px solid ${st.border}`, borderRadius: W * 0.016, fontFamily: 'Inter'}}>
        <div style={{width: W * 0.05, height: W * 0.05, borderRadius: W * 0.012, border: `2px solid ${st.label_color}`, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
          <Check size={W * 0.034} color={st.label_color} />
        </div>
        <div>
          {t.label ? <div style={{fontSize: W * st.size * 0.5, fontWeight: 700, color: 'rgba(255,255,255,0.65)', letterSpacing: 1}}>{up(t.label, 'upper')}</div> : null}
          <div style={{fontSize: W * st.size, fontWeight: st.weight || 800, color: t.label ? st.label_color : st.color}}>{up(t.text, st.case)}</div>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------- carton final
// Thèmes visuels de la fin : fond, encre, accent, matière du bouton
const END_THEMES = {
  nuit: (st) => ({bg: st.bg || '#0d0d10', glow: st.glow || st.accent, ink: st.headline_color || '#fff', accent: st.accent, btnText: st.cta_text || '#fff'}),
  clair: (st) => ({bg: '#f4f1ea', glow: 'transparent', ink: '#111', accent: st.accent, btnText: '#fff', shadow: '0 18px 40px rgba(0,0,0,0.18)'}),
  neon: (st) => ({bg: '#05050a', glow: st.accent, ink: '#fff', accent: st.accent, btnText: st.accent, outline: true, neon: true}),
  degrade: (st) => ({bg: `linear-gradient(160deg, ${st.accent} 0%, #1a0b2e 75%)`, glow: 'transparent', ink: '#fff', accent: '#ffffff', btnText: '#111'}),
  brut: () => ({bg: '#ffd400', glow: 'transparent', ink: '#111', accent: '#111', btnText: '#ffd400', square: true, border: true}),
  verre: (st) => ({bg: '#111', glow: st.accent, ink: '#fff', accent: st.accent, btnText: '#fff', glass: true}),
  pastel: () => ({bg: 'linear-gradient(170deg, #ffe3ec 0%, #e6f0ff 100%)', glow: 'transparent', ink: '#3a2e39', accent: '#ff6f9c', btnText: '#fff', shadow: '0 14px 34px rgba(255,111,156,0.35)'}),
};

const EndCard = ({e, st, brand, W, H}) => {
  const f = useCurrentFrame();
  const anim = e.animation || st.animation || 'pop';
  const th = (END_THEMES[e.theme || st.theme] || END_THEMES.nuit)(st);
  const accent = th.accent;
  const ink = th.ink;
  const lay = e.layout || 'classique';
  const sp = (s, cfg = {}) => spring({frame: f - s, fps: 30, config: {damping: 14, stiffness: 170, ...cfg}});
  // progression d'entrée d'un élément selon l'animation
  const a = (s) => anim === 'bounce' ? sp(s, {damping: 7, stiffness: 120}) : anim === 'flash' ? (f >= 6 ? 1 : 0)
    : anim === 'wipe' ? sp(s + 8) : sp(s);
  // style d'entrée d'un élément
  const E = (s, base = '') => {
    const p = a(s);
    const t = anim === 'slide' ? `translateY(${(1 - p) * H * 0.12}px)`
      : anim === 'zoom' ? `scale(${1.6 - 0.6 * p})`
      : anim === 'bounce' ? `translateY(${(1 - p) * -H * 0.25}px)`
      : anim === 'glitch' ? `translate(${f - s < 12 ? Math.sin((f - s) * 7) * W * 0.02 : 0}px, 0)`
      : anim === 'flash' || anim === 'wipe' ? '' : `scale(${0.85 + 0.15 * p})`;
    return {opacity: Math.min(1, Math.max(0, p)), transform: `${t} ${base}`.trim() || 'translateZ(0)', position: 'relative',
      filter: anim === 'zoom' ? `blur(${(1 - Math.min(1, p)) * 12}px)` : undefined};
  };
  const glitchShadow = (s) => anim === 'glitch' && f - s < 14 ? `${W * 0.008}px 0 #ff2d55, ${-W * 0.008}px 0 #00e5ff` : (th.neon ? `0 0 ${W * 0.03}px ${accent}` : 'none');

  const Btn = ({big, at = 14}) => {
    const pulse = big ? 1 + 0.05 * Math.sin((f - at) / 4) * (f > at + 10 ? 1 : 0) : 1;
    const shape = th.square ? 'square' : (st.button_shape || 'pill');
    const outline = th.outline || shape === 'outline';
    const en = E(at, `scale(${pulse})`);
    return (
      <div style={{padding: `${W * (big ? 0.035 : 0.024)}px ${W * (big ? 0.1 : 0.07)}px`,
        borderRadius: shape === 'square' ? W * 0.012 : W * 0.08,
        background: outline ? 'transparent' : accent, border: outline ? `${W * 0.006}px solid ${accent}` : th.border ? `${W * 0.006}px solid #111` : 'none',
        fontSize: W * (big ? 0.065 : 0.045), fontWeight: 900, color: outline ? accent : th.btnText, ...en,
        boxShadow: th.neon ? `0 0 ${W * 0.05}px ${accent}, inset 0 0 ${W * 0.03}px ${accent}66` : th.border ? `${W * 0.012}px ${W * 0.012}px 0 #111`
          : big ? `0 0 ${W * 0.06}px ${accent}88` : (th.shadow || 'none'), whiteSpace: 'nowrap'}}>
        {st.button_upper === false ? e.cta : up(e.cta, 'upper')}{st.button_arrow === false ? '' : ' →'}</div>
    );
  };
  const Head = ({at = 3, size = st.headline_size, top = H * 0.025}) => {
    if (!e.headline) return null;
    let txt = up(e.headline, 'upper');
    if (anim === 'typewriter') txt = txt.slice(0, Math.max(0, Math.floor((f - at) / 1.4)));
    return (
      <div style={{marginTop: top, fontSize: W * size, fontWeight: 900, letterSpacing: -1, textAlign: 'center', lineHeight: 1.02, padding: `0 ${W * 0.07}px`,
        color: 'inherit', textShadow: glitchShadow(at), ...(anim === 'typewriter' ? {} : E(at))}}>
        {txt}{anim === 'typewriter' && txt.length < up(e.headline, 'upper').length ? <span style={{color: accent}}>|</span> : null}</div>
    );
  };
  const Logo = ({at = 0, top = H * 0.11}) => (st.show_logo || lay === 'minimal') && e.logo_text ? (
    <div style={{marginTop: top, fontSize: W * (lay === 'minimal' ? 0.08 : 0.05), fontWeight: 900, letterSpacing: 4, color: accent, textShadow: glitchShadow(at), ...E(at)}}>{e.logo_text}</div>
  ) : null;
  const Photo = ({at = 6, size = 0.62}) => e.image ? (
    <div style={{marginTop: H * 0.035, width: W * size, height: W * size, borderRadius: th.square ? 0 : W * 0.04, overflow: 'hidden', ...E(at),
      border: th.border ? `${W * 0.008}px solid #111` : th.neon ? `2px solid ${accent}` : 'none',
      boxShadow: th.border ? `${W * 0.015}px ${W * 0.015}px 0 #111` : th.neon ? `0 0 ${W * 0.05}px ${accent}88` : (th.shadow || `0 30px 80px rgba(0,0,0,0.6), 0 0 60px ${th.glow}44`)}}>
      <Img src={staticFile(e.image)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
    </div>
  ) : null;
  const Web = () => e.website ? <div style={{position: 'absolute', bottom: H * 0.075, fontSize: W * 0.03, fontWeight: 700, color: accent}}>{e.website}</div> : null;

  const bg = (
    <>
      {th.glass && e.image
        ? <Img src={staticFile(e.image)} style={{position: 'absolute', width: '100%', height: '100%', objectFit: 'cover', filter: 'blur(36px) brightness(0.55)', transform: 'scale(1.2)'}} />
        : <AbsoluteFill style={{background: th.bg}} />}
      {th.glow !== 'transparent' ? <AbsoluteFill style={{background: `radial-gradient(ellipse at 50% 55%, ${th.glow}55 0%, rgba(0,0,0,0) 60%)`}} /> : null}
      {th.neon ? <AbsoluteFill style={{border: `${W * 0.006}px solid ${accent}`, margin: W * 0.04, borderRadius: W * 0.04, boxShadow: `0 0 ${W * 0.05}px ${accent}, inset 0 0 ${W * 0.05}px ${accent}55`, opacity: a(0)}} /> : null}
      {th.glass ? <AbsoluteFill style={{margin: `${H * 0.07}px ${W * 0.06}px`, borderRadius: W * 0.06, background: 'rgba(255,255,255,0.12)', border: '1.5px solid rgba(255,255,255,0.35)', backdropFilter: 'blur(8px)'}} /> : null}
    </>
  );
  const fx = (
    <>
      {anim === 'flash' ? <AbsoluteFill style={{background: '#fff', opacity: interpolate(f, [0, 2, 8], [0, 1, 0], CL)}} /> : null}
      {anim === 'wipe' ? <AbsoluteFill style={{background: accent, transform: `translateX(${interpolate(f, [0, 8, 16], [-100, 0, 100], CL)}%)`}} /> : null}
    </>
  );
  const wrap = (children, background = bg) => (
    <AbsoluteFill style={{fontFamily: 'Inter', color: ink, alignItems: 'center'}}>{background}{children}{fx}</AbsoluteFill>
  );

  if (lay === 'superpose') {
    const back = (
      <>
        {e.image ? <Img src={staticFile(e.image)} style={{position: 'absolute', width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${1.04 + 0.03 * f / 90})`}} /> : bg}
        <AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(0,0,0,0.15) 30%, rgba(0,0,0,0.8) 75%)'}} />
      </>
    );
    return wrap(<>
      <div style={{position: 'absolute', bottom: H * 0.3, width: '100%', display: 'flex', justifyContent: 'center'}}><div style={{color: '#fff'}}><Head at={2} size={st.headline_size * 0.9} top={0} /></div></div>
      <div style={{position: 'absolute', bottom: H * 0.17}}><Btn at={8} /></div><Web />
    </>, back);
  }
  if (lay === 'bouton') {
    const hand = interpolate((f - 22) % 30, [0, 10, 20, 30], [0, -W * 0.02, 0, 0], CL);
    return wrap(<>
      <Logo /><Head />
      <div style={{position: 'absolute', top: H * 0.5, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
        <Btn big at={8} />
        <svg width={W * 0.12} height={W * 0.12} viewBox="0 0 24 24" style={{marginTop: W * 0.02, opacity: a(18), transform: `translate(${W * 0.12}px, ${hand}px) rotate(-20deg)`}}>
          <path fill={ink} d="M9 11V5.5a1.5 1.5 0 013 0V10h.5V8.5a1.5 1.5 0 013 0V10h.5v-.5a1.5 1.5 0 013 0V15c0 3.3-2.7 6-6 6h-1.2c-1.7 0-3.3-.8-4.3-2.2L4.1 14a1.5 1.5 0 012.3-1.9L9 14z" /></svg>
      </div><Web />
    </>);
  }
  if (lay === 'offre' || lay === 'garantie') {
    const blink = lay === 'offre' ? 0.75 + 0.25 * Math.abs(Math.sin(f / 6)) : 1;
    const en = E(2);
    return wrap(<>
      <Logo />
      <div style={{marginTop: H * 0.06, display: 'flex', alignItems: 'center', gap: W * 0.02, padding: `${W * 0.02}px ${W * 0.05}px`, borderRadius: th.square ? 0 : W * 0.06,
        background: lay === 'offre' ? '#ff2d55' : 'transparent', color: lay === 'offre' ? '#fff' : ink, border: lay === 'garantie' ? `3px solid ${accent}` : 'none',
        fontSize: W * 0.05, fontWeight: 900, ...en, opacity: en.opacity * blink}}>
        <svg width={W * 0.05} height={W * 0.05} viewBox="0 0 24 24"><path fill="currentColor" d={lay === 'offre'
          ? 'M13 2s1 3-1 6c-1.5 2.2-4 3.5-4 7a5 5 0 0010 0c0-2-1-3.5-1-3.5s-.5 2-2 2.5c1-3-1-6-2-12z'
          : 'M12 2l8 3v6c0 5-3.4 9.4-8 11-4.6-1.6-8-6-8-11V5z'} /></svg>{up(e.badge, 'upper')}
      </div>
      <Head at={6} /><Photo at={9} size={0.5} />
      <div style={{position: 'absolute', bottom: H * 0.12}}><Btn at={14} /></div><Web />
    </>);
  }
  if (lay === 'avis') {
    return wrap(<>
      <Logo />
      <div style={{marginTop: H * 0.1, display: 'flex', gap: W * 0.012, ...E(2)}}>{[0, 1, 2, 3, 4].map((i) => (
        <svg key={i} width={W * 0.085} height={W * 0.085} viewBox="0 0 24 24" style={{transform: `scale(${a(2 + i * 2)})`}}><path fill="#FFC531" d="M12 2l2.9 6.6 7.1.6-5.4 4.7 1.6 7L12 17.3 5.8 20.9l1.6-7L2 9.2l7.1-.6z" /></svg>
      ))}</div>
      <div style={{marginTop: H * 0.03, fontSize: W * 0.07, fontWeight: 800, textAlign: 'center', padding: `0 ${W * 0.08}px`, lineHeight: 1.15, ...E(5)}}>“{e.quote}”</div>
      <div style={{marginTop: H * 0.02, fontSize: W * 0.032, color: '#2e9e5b', fontWeight: 700, ...E(8)}}>✓ Verified buyer</div>
      <Photo at={10} size={0.42} />
      <div style={{position: 'absolute', bottom: H * 0.12}}><Btn at={14} /></div><Web />
    </>);
  }
  if (lay === 'question') {
    return wrap(<>
      <div style={{position: 'absolute', top: H * 0.3, width: '100%', display: 'flex', justifyContent: 'center'}}><Head at={2} size={st.headline_size * 1.15} top={0} /></div>
      <div style={{position: 'absolute', top: H * 0.58}}><Btn big at={12} /></div><Web />
    </>);
  }
  if (lay === 'minimal') {
    return wrap(<>
      <div style={{position: 'absolute', top: H * 0.36, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
        <Logo top={0} />
        <div style={{width: W * 0.12 * Math.min(1, a(4)), height: 3, background: accent, margin: `${H * 0.025}px 0`}} />
        <Btn at={8} />
      </div><Web />
    </>);
  }
  return wrap(<>
    <Logo /><Head /><Photo />
    {st.show_bullets ? (
      <div style={{marginTop: H * 0.03, display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: W * 0.018, padding: `0 ${W * 0.06}px`}}>
        {e.bullets.map((b, i) => (
          <div key={i} style={{padding: `${W * 0.012}px ${W * 0.026}px`, borderRadius: th.square ? 0 : W * 0.05, border: `2px solid ${ink}33`, background: `${ink}0d`,
            fontSize: W * 0.032, fontWeight: 800, ...E(9 + i * 3)}}>{up(b, 'upper')}</div>
        ))}
      </div>
    ) : null}
    {e.cta ? <div style={{position: 'absolute', bottom: H * 0.12}}><Btn at={14} /></div> : null}<Web />
  </>);
};

// ---------------------------------------------------------------- musique avec ducking
const duckVolume = (m) => (f) => {
  let v = m.volume;
  for (const [a, b] of m.ranges) {
    if (f >= a - 6 && f <= b + 8) {
      const k = Math.min(interpolate(f, [a - 6, a], [0, 1], CL), interpolate(f, [b, b + 8], [1, 0], CL));
      v = Math.min(v, m.volume + (m.duck_to - m.volume) * k);
    }
  }
  return v;
};

export const Edit = (p) => {
  const {width: W, height: H, style, clips, voice, music, subtitles, tags, hook, end, brand, overlays = [], broll} = p;
  const img = style.image || {};
  return (
    <AbsoluteFill style={{background: '#000'}}>
      {clips.map((c, i) => (
        <Sequence key={i} from={c.from} durationInFrames={c.dur}><Clip c={c} img={img} broll={broll} /></Sequence>
      ))}
      {img.bottom_gradient ? (
        <AbsoluteFill style={{background: `linear-gradient(180deg, rgba(0,0,0,0) ${(img.gradient_start || 0.45) * 100}%, rgba(0,0,0,${img.bottom_gradient}) 100%)`}} />
      ) : null}
      {hook ? <Sequence from={hook.from} durationInFrames={hook.to - hook.from}><Hook hook={hook} st={style.hook_title} W={W} H={H} /></Sequence> : null}
      {tags.map((t, i) => (
        <Sequence key={i} from={t.from} durationInFrames={t.to - t.from}><Tag t={t} st={style.tags} W={W} H={H} /></Sequence>
      ))}
      <Subtitles subs={subtitles} st={style.subtitles} W={W} H={H} />
      {overlays.map((o, i) => (
        <Sequence key={`o${i}`} from={o.from} durationInFrames={Math.max(1, o.to - o.from)}><Overlay o={o} W={W} H={H} accent={style.accent || brand.accent || '#ff6a00'} /></Sequence>
      ))}
      {img.letterbox ? (
        <>
          <div style={{position: 'absolute', top: 0, left: 0, right: 0, height: H * img.letterbox, background: '#000'}} />
          <div style={{position: 'absolute', bottom: 0, left: 0, right: 0, height: H * img.letterbox, background: '#000'}} />
        </>
      ) : null}
      {end ? <Sequence from={end.from} durationInFrames={end.dur}><EndCard e={end} st={style.end_card} brand={brand} W={W} H={H} /></Sequence> : null}
      {voice.map((v, i) => (
        <Sequence key={i} from={v.from}><Audio src={staticFile(v.src)} volume={v.volume} /></Sequence>
      ))}
      {music ? <Audio src={staticFile(music.src)} volume={duckVolume(music)} /> : null}
    </AbsoluteFill>
  );
};
