import React, { useState } from "react";
import { cn } from "../../lib/cn";

type SmartImageProps = {
  src?: string;
  alt: string;
  className?: string;
  /** Intrinsic size: set to reserve layout space and avoid CLS (perf audit). */
  width?: number;
  height?: number;
  /** CSS gradient shown as the placeholder / when no real image is wired up yet. */
  gradient?: [string, string] | string[];
};

/**
 * Blur-up image with a shimmer skeleton. Falls back to a gradient block (our
 * placeholder art) when `src` isn't provided, so the loading pattern is still
 * exercised until real assets replace the placeholders (master rule #2).
 */
export const SmartImage: React.FC<SmartImageProps> = ({ src, alt, className, width, height, gradient }) => {
  const [loaded, setLoaded] = useState(false);

  const gradientBg =
    gradient && Array.isArray(gradient)
      ? `linear-gradient(135deg, ${gradient[0]}, ${gradient[1]})`
      : (gradient as string | undefined);

  if (!src) {
    return (
      <div
        className={cn("relative overflow-hidden", className)}
        style={{ background: gradientBg ?? "var(--color-page, #EDEFE6)" }}
        role="img"
        aria-label={alt}
      />
    );
  }

  return (
    <div className={cn("relative overflow-hidden", className)} style={{ background: gradientBg }}>
      {!loaded && <div className="shimmer absolute inset-0" aria-hidden />}
      <img
        src={src}
        alt={alt}
        loading="lazy"
        decoding="async"
        width={width}
        height={height}
        onLoad={() => setLoaded(true)}
        className={cn(
          "h-full w-full object-cover transition-all duration-700 ease-out",
          loaded ? "scale-100 opacity-100 blur-0" : "scale-105 opacity-0 blur-md",
        )}
      />
    </div>
  );
};

export default SmartImage;
