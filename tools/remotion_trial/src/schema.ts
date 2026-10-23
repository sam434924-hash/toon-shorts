import { z } from "zod";

export const WordTimingSchema = z.object({
  word: z.string(),
  start_ms: z.number().nonnegative(),
  end_ms: z.number().nonnegative(),
});

export const KineticWordsPropsSchema = z.object({
  text: z.string().max(80),
  highlightTerm: z.string().optional(),
  highlightColor: z.string().regex(/^#[0-9a-fA-F]{6}$/).default("#38bdf8"),
  startFrame: z.number().int().nonnegative(),
  durationFrames: z.number().int().positive().default(24),
  fontSize: z.number().int().positive().default(48),
});

export const DiagramFlowPropsSchema = z.object({
  nodes: z.array(z.string().max(40)).min(2).max(6),
  arrows: z.array(z.string().max(20)).max(5).default(["req", "res"]),
  startFrame: z.number().int().nonnegative(),
  durationFrames: z.number().int().positive().default(45),
  strokeColor: z.string().regex(/^#[0-9a-fA-F]{6}$/).default("#38bdf8"),
  nodeBg: z.string().default("rgba(15, 23, 42, 0.9)"),
});

export const OverlayScenePropsSchema = z.object({
  fps: z.number().int().positive().default(30),
  durationInFrames: z.number().int().positive().default(150),
  width: z.number().int().positive().default(1080),
  height: z.number().int().positive().default(1920),
  kineticWords: KineticWordsPropsSchema,
  diagramFlow: DiagramFlowPropsSchema,
});

export type OverlaySceneProps = z.infer<typeof OverlayScenePropsSchema>;
