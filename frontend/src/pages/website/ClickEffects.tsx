import { useEffect, useRef, useState, type CSSProperties } from "react";

interface ClickEffect {
  id: number;
  x: number;
  y: number;
}

const particleAngles = Array.from({ length: 8 }, (_, index) => index * 45);

export default function ClickEffects() {
  const [effects, setEffects] = useState<ClickEffect[]>([]);
  const nextId = useRef(0);

  useEffect(() => {
    const handleClick = (event: MouseEvent) => {
      if (
        event.detail === 0 ||
        window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
        !(event.target instanceof Element) ||
        !event.target.closest(".aperture-app")
      ) {
        return;
      }

      const effect = { id: nextId.current++, x: event.clientX, y: event.clientY };
      setEffects((current) => [...current.slice(-5), effect]);
    };

    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, []);

  const removeEffect = (id: number) => {
    setEffects((current) => current.filter((effect) => effect.id !== id));
  };

  return (
    <div className="click-effects-layer" aria-hidden="true">
      {effects.map((effect) => (
        <div
          className="click-effect"
          key={effect.id}
          onAnimationEnd={(event) => {
            if (event.target === event.currentTarget) {
              removeEffect(effect.id);
            }
          }}
          style={{ left: effect.x, top: effect.y }}
        >
          <svg className="click-effect-svg" viewBox="0 0 72 72">
            <circle className="click-effect-ring" cx="36" cy="36" r="8" />
            <path className="click-effect-crosshair" d="M36 7v15 M36 50v15 M7 36h15 M50 36h15" />
          </svg>
          {particleAngles.map((angle) => (
            <span
              className="click-effect-particle"
              key={angle}
              style={{ "--particle-angle": `${angle}deg` } as CSSProperties}
            />
          ))}
        </div>
      ))}
    </div>
  );
}
