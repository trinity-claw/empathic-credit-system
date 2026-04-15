"use client";

import { useEffect, useRef } from "react";

export function WebGLRings() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let time = 0;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    resize();
    window.addEventListener("resize", resize);

    const draw = () => {
      const { width: w, height: h } = canvas;
      ctx.clearRect(0, 0, w, h);

      const cx = w / 2;
      const cy = h / 2;
      const base = Math.min(w, h);

      for (let i = 0; i < 6; i++) {
        const phase = time * 0.5 + i * 1.05;
        const radius = (0.08 + i * 0.11 + Math.sin(phase) * 0.015) * base;
        const alpha = (1 - i * 0.12) * 0.14;
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(0, 230, 118, ${alpha})`;
        ctx.lineWidth = 1.2 + i * 0.35;
        ctx.stroke();
      }

      time += 0.018;
      animId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className="fixed inset-0 z-0 pointer-events-none opacity-50"
    />
  );
}
