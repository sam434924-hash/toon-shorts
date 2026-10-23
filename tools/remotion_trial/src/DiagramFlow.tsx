import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { DiagramFlowPropsSchema } from "./schema";
import { z } from "zod";

type DiagramFlowProps = z.infer<typeof DiagramFlowPropsSchema>;

export const DiagramFlow: React.FC<DiagramFlowProps> = (props) => {
  const validated = DiagramFlowPropsSchema.parse(props);
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const relFrame = frame - validated.startFrame;
  if (relFrame < 0) {
    return null;
  }

  const { nodes, arrows, durationFrames, strokeColor, nodeBg } = validated;
  const stages = Math.max(1, nodes.length * 2 - 1);
  const progress = Math.min(1, Math.max(0, relFrame / durationFrames));

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 20,
        width: "100%",
      }}
    >
      {nodes.map((nodeLabel, nIdx) => {
        const nodeThreshold = (2 * nIdx) / stages;
        const nodeProgress = Math.min(1, Math.max(0, (progress - nodeThreshold) * stages));
        const nodeSpring = spring({
          frame: Math.max(0, relFrame - (nodeThreshold * durationFrames)),
          fps,
          config: {
            damping: 14,
            mass: 0.6,
            stiffness: 140,
          },
        });

        const showNode = progress >= nodeThreshold;
        const arrowIdx = nIdx;
        const showArrow = nIdx < nodes.length - 1;
        const arrowThreshold = (2 * nIdx + 1) / stages;
        const arrowProgress = Math.min(1, Math.max(0, (progress - arrowThreshold) * stages));

        return (
          <React.Fragment key={nIdx}>
            <div
              style={{
                opacity: showNode ? 1 : 0,
                transform: `scale(${showNode ? nodeSpring : 0})`,
                backgroundColor: nodeBg,
                border: `3px solid ${strokeColor}`,
                borderRadius: 16,
                padding: "16px 26px",
                boxShadow: "0 8px 24px rgba(0,0,0,0.35)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <span
                style={{
                  fontFamily: 'Inter, system-ui, sans-serif',
                  fontSize: 32,
                  fontWeight: 800,
                  color: "#ffffff",
                }}
              >
                {nodeLabel}
              </span>
            </div>

            {showArrow && (
              <div
                style={{
                  opacity: progress >= arrowThreshold ? 1 : 0,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: 70,
                  height: 30,
                }}
              >
                <svg viewBox="0 0 70 30" width="70" height="30">
                  <path
                    d="M 6 15 L 56 15"
                    stroke={strokeColor}
                    strokeWidth={4}
                    strokeLinecap="round"
                    strokeDasharray={50}
                    strokeDashoffset={50 * (1 - arrowProgress)}
                  />
                  <path
                    d="M 50 8 L 62 15 L 50 22"
                    fill="none"
                    stroke={strokeColor}
                    strokeWidth={4}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeDasharray={30}
                    strokeDashoffset={30 * (1 - arrowProgress)}
                  />
                </svg>
              </div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};
