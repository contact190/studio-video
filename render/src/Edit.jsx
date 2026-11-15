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
const EndCard = ({e, st, brand, W, H}) => {
  const f = useCurrentFrame();
  const a = (s) => spring({frame: f - s, fps: 30, config: {damping: 14, stiffness: 170}});
  return (
    <AbsoluteFill style={{background: st.bg, fontFamily: 'Inter', color: '#fff', alignItems: 'center'}}>
      <AbsoluteFill style={{background: `radial-gradient(ellipse at 50% 55%, ${st.glow}55 0%, rgba(0,0,0,0) 60%)`}} />
      {st.show_logo ? <div style={{marginTop: H * 0.11, fontSize: W * 0.05, fontWeight: 900, letterSpacing: 4, color: st.accent, opacity: a(0)}}>{e.logo_text}</div> : null}
      <div style={{marginTop: H * 0.025, fontSize: W * st.headline_size, fontWeight: 900, letterSpacing: -1, textAlign: 'center', lineHeight: 1, padding: `0 ${W * 0.06}px`, color: st.headline_color || '#fff',
        opacity: a(3), transform: `scale(${0.9 + 0.1 * a(3)})`}}>{up(e.headline, 'upper')}</div>
      {e.image ? (
        <div style={{marginTop: H * 0.035, width: W * 0.62, height: W * 0.62, borderRadius: W * 0.04, overflow: 'hidden', opacity: a(6),
          transform: `translateY(${(1 - a(6)) * 40}px)`, boxShadow: `0 30px 80px rgba(0,0,0,0.6), 0 0 60px ${st.glow}44`}}>
          <Img src={staticFile(e.image)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        </div>
      ) : null}
      {st.show_bullets ? (
        <div style={{marginTop: H * 0.03, display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: W * 0.018, padding: `0 ${W * 0.06}px`}}>
          {e.bullets.map((b, i) => (
            <div key={i} style={{padding: `${W * 0.012}px ${W * 0.026}px`, borderRadius: W * 0.05, border: '2px solid rgba(255,255,255,0.22)', background: 'rgba(255,255,255,0.06)',
              fontSize: W * 0.032, fontWeight: 800, opacity: a(9 + i * 3)}}>{up(b, 'upper')}</div>
          ))}
        </div>
      ) : null}
      {e.cta ? (
        <div style={{position: 'absolute', bottom: H * 0.12, padding: `${W * 0.024}px ${W * 0.07}px`, borderRadius: W * 0.06, background: st.accent,
          fontSize: W * 0.045, fontWeight: 900, color: st.cta_text || brand.accent_text || '#fff', opacity: a(14), transform: `scale(${0.85 + 0.15 * a(14)})`}}>{up(e.cta, 'upper')} →</div>
      ) : null}
      {e.website ? <div style={{position: 'absolute', bottom: H * 0.075, fontSize: W * 0.03, fontWeight: 700, color: st.accent}}>{e.website}</div> : null}
    </AbsoluteFill>
  );
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
