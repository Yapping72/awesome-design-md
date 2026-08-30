import { useEffect, useState } from "react";

/**
 * Recharts renders tick/axis/tooltip colors as literal SVG attribute
 * values, not through the CSS cascade, so `var(--text-dim)` doesn't
 * reliably work there — this reads the actual resolved color from the
 * current theme and re-reads it whenever ThemeToggle flips the theme.
 */
export interface ChartColors {
  textDim: string;
  panelBorder: string;
  panel: string;
  text: string;
  green: string;
  red: string;
}

function readChartColors(): ChartColors {
  const styles = getComputedStyle(document.documentElement);
  const get = (name: string) => styles.getPropertyValue(name).trim();
  return {
    textDim: get("--text-dim"),
    panelBorder: get("--panel-border"),
    panel: get("--panel"),
    text: get("--text"),
    green: get("--green"),
    red: get("--red"),
  };
}

export function useChartColors(): ChartColors {
  const [colors, setColors] = useState<ChartColors>(readChartColors);

  useEffect(() => {
    function handleThemeChange() {
      setColors(readChartColors());
    }
    window.addEventListener("themechange", handleThemeChange);
    return () => window.removeEventListener("themechange", handleThemeChange);
  }, []);

  return colors;
}
