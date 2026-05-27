---
name: google-branding
description: Apply Google's official brand colors and typography to artifacts. Use when creating documents, presentations, websites, or any visual content that should follow Google's brand guidelines, design standards, or look-and-feel. Includes official color hex codes, typography recommendations, and implementation patterns.
---

# Google Branding

Apply Google's official brand colors (#4285F4 blue, #EA4335 red, #FBBC05 yellow, #34A853 green) and typography guidelines to create artifacts with Google's distinctive look-and-feel.

## When to Use This Skill

Use this skill when:
- Creating artifacts that should match Google's brand identity
- User requests Google colors, brand colors, or visual style guidelines
- Building presentations, documents, or websites with Google's aesthetic
- Implementing Google's design language or Material Design
- User mentions wanting a "Google look" or references Google's branding

## Quick Reference

**Colors:**
- Blue: `#4285F4` (primary)
- Red: `#EA4335` (accent)
- Yellow: `#FBBC05` (highlight)
- Green: `#34A853` (success)

**Typography:**
- Use Roboto for body text (open-source Google font)
- Use Poppins or Roboto for headings
- Avoid proprietary Google Sans (restricted to official Google use)

## Instructions

### 1. Review Guidelines First

Before creating any artifact with Google branding, read the comprehensive reference:
- [colors-and-typography.md](references/colors-and-typography.md) - Complete color codes, typography guidelines, and implementation examples

### 2. Apply Colors Consistently

Use Google's four official brand colors:
```css
:root {
  --google-blue: #4285F4;
  --google-red: #EA4335;
  --google-yellow: #FBBC05;
  --google-green: #34A853;
}
```

- Use Blue as the primary color (60-70% of color usage)
- Use Red, Yellow, and Green as accents (30-40% combined)
- Never modify these exact hex values

### 3. Typography Implementation

For HTML/React artifacts:
```html
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
```

For documents (DOCX/PPTX):
- Use Roboto if available, otherwise Arial or another clean sans-serif
- Maintain consistent font weights (Regular 400, Medium 500, Bold 700)

### 4. Design Principles

Follow Google's design philosophy:
- **Simple and clean** - Avoid clutter, embrace whitespace
- **Geometric and modern** - Use clean lines and shapes
- **Accessible** - Ensure proper color contrast for readability
- **Playful** - The four-color palette conveys approachability

### 5. Common Patterns

**For React/HTML artifacts:**
- Use CSS variables for colors
- Import Roboto from Google Fonts
- Apply consistent spacing and clean layouts

**For DOCX/PPTX artifacts:**
- Set theme colors to the four Google colors
- Use Roboto or clean sans-serif fonts
- Create visual hierarchy with color accents

## Examples

### HTML/React Color Application
```css
.header {
  background-color: var(--google-blue);
  color: white;
}

.cta-button {
  background-color: var(--google-red);
  color: white;
}

.success-message {
  border-left: 4px solid var(--google-green);
}

.highlight {
  background-color: var(--google-yellow);
}
```

### Multi-Color Logo/Header Style
Use all four colors in sequence for a distinctive Google feel:
- Blue for main elements
- Red, Yellow, Green as accent bars, borders, or icons

## Resources

- **references/colors-and-typography.md** - Comprehensive guide with all color codes, typography details, implementation patterns, and design principles. Read this for detailed information about specific use cases.

## Notes

- Google Sans and Product Sans are proprietary - use Roboto or Poppins as alternatives
- Official colors are verified from Google's brand guidelines
- These guidelines help create artifacts that feel cohesive with Google's design language while respecting trademark and licensing restrictions
