import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { KineticWordsPropsSchema } from "./schema";
import { z } from "zod";

type KineticWordsProps = z.infer<typeof KineticWordsPropsSchema>;

export const KineticWords: React.FC<KineticWordsProps> = (props) => {
  const validated = KineticWordsPropsSchema.parse(props);
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const relFrame = frame - validated.startFrame;
  if (relFrame < 0) {
    return null;
  }

  const scaleSpring = spring({
    frame: relFrame,
    fps,
    config: {
      damping: 12,
      mass: 0.5,
      stiffness: 160,
    },
  });

  const words = validated.text.split(/\s+/);
  const highlightLower = (validated.highlightTerm || "").toLowerCase().replace(/[^a-z0-9]/g, "");

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 12,
        transform: `scale(${scaleSpring})`,
        willChange: "transform",
      }}
    >
      {words.map((w, idx) => {
        const cleanW = w.toLowerCase().replace(/[^a-z0-9]/g, "");
        const isHighlight =
          highlightLower &&
          (cleanW === highlightLower ||
            highlightLower.includes(cleanW) ||
            cleanW.includes(highlightLower));

        return (
          <span
            key={idx}
            style={{
              fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
              fontSize: validated.fontSize,
              fontWeight: isHighlight ? 900 : 700,
              color: isHighlight ? validated.highlightColor : "#ffffff",
              textShadow: "0 4px 18px rgba(0, 0, 0, 0.45)",
              borderBottom: isHighlight ? `4px solid ${validated.highlightColor}` : "none",
              paddingBottom: isHighlight ? 4 : 0,
            }}
          >
            {w}
          </span>
        );
      })}
    </div>
  );
};
