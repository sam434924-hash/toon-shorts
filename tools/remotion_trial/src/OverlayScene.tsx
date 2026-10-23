import React from "react";
import { AbsoluteFill } from "remotion";
import { KineticWords } from "./KineticWords";
import { DiagramFlow } from "./DiagramFlow";
import { OverlayScenePropsSchema, OverlaySceneProps } from "./schema";

export const OverlayScene: React.FC<OverlaySceneProps> = (props) => {
  const validated = OverlayScenePropsSchema.parse(props);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "transparent",
        pointerEvents: "none",
        width: validated.width,
        height: validated.height,
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 350,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
        }}
      >
        <KineticWords {...validated.kineticWords} />
      </div>

      <div
        style={{
          position: "absolute",
          top: 650,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          padding: "0 60px",
        }}
      >
        <DiagramFlow {...validated.diagramFlow} />
      </div>
    </AbsoluteFill>
  );
};
