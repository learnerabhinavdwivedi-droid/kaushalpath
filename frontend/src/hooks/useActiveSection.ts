import { useEffect, useState } from "react";

/**
 * Returns the id of the section currently in view (for nav active highlighting).
 * A band across the middle of the viewport decides "active".
 */
export function useActiveSection(ids: string[]): string {
  const [active, setActive] = useState("");
  const key = ids.join(",");

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) setActive(entry.target.id);
        });
      },
      { rootMargin: "-45% 0px -50% 0px", threshold: 0 },
    );

    ids.forEach((id) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return active;
}
