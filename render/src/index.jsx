import React from 'react';
import {registerRoot, Composition, delayRender, continueRender} from 'remotion';
import '@fontsource/inter/500.css';
import '@fontsource/inter/700.css';
import '@fontsource/inter/800.css';
import '@fontsource/inter/900.css';
import {Edit} from './Edit';

const h = delayRender('fonts');
Promise.all(['500 40px Inter', '700 40px Inter', '800 40px Inter', '900 40px Inter'].map((s) => document.fonts.load(s)))
  .then(() => continueRender(h)).catch(() => continueRender(h));

const Root = () => (
  <Composition
    id="Edit"
    component={Edit}
    fps={30}
    width={1080}
    height={1920}
    durationInFrames={30}
    defaultProps={{width: 1080, height: 1920, fps: 30, durationInFrames: 30, clips: [], voice: [], subtitles: [], tags: [], style: {}, brand: {}}}
    calculateMetadata={({props}) => ({durationInFrames: props.durationInFrames, width: props.width, height: props.height, fps: props.fps})}
  />
);
registerRoot(Root);
