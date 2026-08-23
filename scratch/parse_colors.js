
const colors = {
  "surface-bright": "#3a3939",
  "on-primary-container": "#636565",
  "primary": "#ffffff",
  "on-secondary": "#2f3037",
  "background": "#141313",
  "surface-dim": "#141313",
  "on-primary": "#2f3131",
  "outline": "#8e9192",
  "error-container": "#93000a",
  "surface-container-high": "#2a2a2a",
  "surface-container-low": "#1c1b1b",
  "on-tertiary-fixed": "#1a1c1c",
  "on-tertiary-container": "#636565",
  "on-surface-variant": "#c4c7c8",
  "secondary-fixed": "#e2e1eb",
  "on-background": "#e5e2e1",
  "on-secondary-fixed-variant": "#45464e",
  "tertiary-fixed": "#e2e2e2",
  "tertiary-fixed-dim": "#c6c6c7",
  "on-error-container": "#ffdad6",
  "primary-fixed": "#e2e2e2",
  "surface-variant": "#353434",
  "tertiary-container": "#e2e2e2",
  "error": "#ffb4ab",
  "on-primary-fixed-variant": "#454747",
  "outline-variant": "#444748",
  "surface-container-lowest": "#0e0e0e",
  "on-tertiary": "#2f3131",
  "inverse-on-surface": "#313030",
  "surface-tint": "#c6c6c7",
  "on-error": "#690005",
  "tertiary": "#ffffff",
  "on-surface": "#e5e2e1",
  "secondary": "#c6c6cf",
  "surface": "#141313",
  "primary-fixed-dim": "#c6c6c7",
  "surface-container": "#201f1f",
  "primary-container": "#e2e2e2",
  "on-secondary-container": "#b4b4bd",
  "secondary-fixed-dim": "#c6c6cf",
  "on-secondary-fixed": "#1a1b22",
  "secondary-container": "#45464e",
  "inverse-primary": "#5d5f5f",
  "inverse-surface": "#e5e2e1",
  "on-primary-fixed": "#1a1c1c",
  "surface-container-highest": "#353434",
  "on-tertiary-fixed-variant": "#454747"
};

const shadcnCollisions = ["background", "foreground", "primary", "secondary", "muted", "accent", "destructive", "border", "input", "ring"];
let themeVars = "";
let cssVars = "";

for (const [key, value] of Object.entries(colors)) {
  if (shadcnCollisions.includes(key)) {
    // It is a collision, so we add a prefix in the theme to avoid global collision
    // Actually, if we prefix it, we have to change the HTML string.
    // Better to just define it as a custom property in @theme without renaming, wait:
    // If we define --color-primary in @theme, it globally changes text-primary to #ffffff.
    // That breaks Shadcn.
    console.log(`Collision: ${key}`);
  } else {
    themeVars += `  --color-${key}: ${value};\n`;
  }
}

console.log("THEME VARS:");
console.log(themeVars);

