import React from "react";
import { Composition } from "remotion";
import { OverlayScene } from "./OverlayScene";
import { OverlayScenePropsSchema } from "./schema";

const defaultProps = {
  fps: 30,
  durationInFrames: 120, // 4 seconds @ 30fps
  width: 1080,
  height: 1920,
  kineticWords: {
    text: "How APIs Work",
    highlightTerm: "APIs",
    highlightColor: "#38bdf8",
    startFrame: 15,
    durationFrames: 25,
    fontSize: 54,
  },
  diagramFlow: {
    nodes: ["Client", "Gateway", "Server"],
    arrows: ["req", "res"],
    startFrame: 35,
    durationFrames: 45,
    strokeColor: "#38bdf8",
    nodeBg: "rgba(15, 23, 42, 0.95)",
  },
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="OverlayScene"
      component={OverlayScene}
      durationInFrames={120}
      fps={30}
      width={1080}
      height={1920}
      schema={OverlayScenePropsSchema}
      defaultProps={defaultProps}
    />
  );
};
