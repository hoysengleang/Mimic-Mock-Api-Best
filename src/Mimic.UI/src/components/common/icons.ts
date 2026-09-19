/**
 * The icon set.
 *
 * Hand-inlined rather than pulled from a package: the app needs about twenty
 * glyphs, and shipping a whole icon library for that is dead weight. All are
 * drawn on a 24px grid with a 1.75 stroke so they sit together optically.
 */

export const ICON_PATHS = {
  // Navigation & structure
  collection:
    '<path d="M4 6.5A1.5 1.5 0 0 1 5.5 5h3.2a1.5 1.5 0 0 1 1.2.6l.8 1.1a1.5 1.5 0 0 0 1.2.6h5.6A1.5 1.5 0 0 1 19 8.8v8.7a1.5 1.5 0 0 1-1.5 1.5h-12A1.5 1.5 0 0 1 4 17.5Z"/>',
  chevron: '<path d="m9.5 6 6 6-6 6"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  close: '<path d="m6 6 12 12M18 6 6 18"/>',
  search: '<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4 4"/>',
  play: '<path d="M7 5.5v13l11-6.5Z" stroke-linejoin="round"/>',
  send: '<path d="M21 3 10.5 13.5M21 3l-6.8 18-3.7-7.5L3 9.8Z" stroke-linejoin="round"/>',

  // Sections
  mock: '<path d="M13 3 4.5 13.5h6L11 21l8.5-10.5h-6Z" stroke-linejoin="round"/>',
  runner: '<path d="M4 6h9M4 12h16M4 18h12"/><circle cx="17" cy="6" r="2.2"/>',
  history: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
  variable:
    '<circle cx="8.5" cy="12" r="3.5"/><path d="M12 12h8.5M17.5 12v3"/>',

  // Actions
  copy: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5.5 15H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h9a1 1 0 0 1 1 1v.5"/>',
  edit: '<path d="M4 20h4L19 9a2.1 2.1 0 0 0-3-3L5 17Z" stroke-linejoin="round"/>',
  trash: '<path d="M4 7h16M10 7V5h4v2M6 7l1 13h10l1-13"/>',
  refresh: '<path d="M20 12a8 8 0 1 1-2.6-5.9M20 4v5h-5"/>',
  download: '<path d="M12 4v11m0 0 4-4m-4 4-4-4M5 19h14"/>',

  // State
  check: '<path d="m5 12.5 4.5 4.5L19 7.5" stroke-linejoin="round"/>',
  alert: '<circle cx="12" cy="12" r="8.5"/><path d="M12 8v5M12 16.2v.2"/>',
  info: '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5M12 7.8v.2"/>',

  // Theme
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.2 5.2l1.4 1.4M17.4 17.4l1.4 1.4M18.8 5.2l-1.4 1.4M6.6 17.4l-1.4 1.4"/>',
  moon: '<path d="M20 14.2A8.5 8.5 0 0 1 9.8 4 8.5 8.5 0 1 0 20 14.2Z" stroke-linejoin="round"/>',
  terminal:
    '<rect x="3" y="4.5" width="18" height="15" rx="2.5"/><path d="m7.5 10 2.5 2.2-2.5 2.2M12.5 14.8h4"/>',

  // Response / empty states
  response:
    '<path d="M4 6v6a3 3 0 0 0 3 3h13m0 0-4-4m4 4-4 4" stroke-linejoin="round"/>',
  request: '<path d="M4 12h12m0 0-4-4m4 4-4 4M20 5v14"/>',
} as const

export type IconName = keyof typeof ICON_PATHS
