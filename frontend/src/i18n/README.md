# Internationalization (i18n) Implementation

## Overview

This directory contains the internationalization configuration and translation files for the MCP Platform Frontend application.

## Structure

```
i18n/
├── config.ts           # i18n configuration and initialization
├── locales/            # Translation files
│   ├── en.json        # English translations
│   └── zh.json        # Chinese translations
├── __tests__/         # i18n tests
│   └── i18n.test.ts   # Configuration and translation tests
└── README.md          # This file
```

## Files

### config.ts

Initializes and configures i18next with:
- Language resources (English and Chinese)
- Saved language preference from localStorage
- Fallback language (English)
- React integration

### locales/en.json

English translations organized by feature:
- common: General UI elements
- auth: Authentication
- nav: Navigation
- dashboard: Dashboard
- tools: MCP Tools
- knowledge: Knowledge Base
- analysis: AI Analysis
- github: GitHub Integration
- deployments: Deployments
- apiKeys: API Keys
- errors: Error messages
- settings: Settings
- pagination: Pagination
- validation: Form validation

### locales/zh.json

Chinese translations matching the English structure.

## Usage

### Basic Translation

```typescript
import { useI18n } from '@/hooks/useI18n';

function MyComponent() {
  const { t } = useI18n();
  
  return <h1>{t('common.loading')}</h1>;
}
```

### With Interpolation

```typescript
const { t } = useI18n();

// English: "Username is required"
// Chinese: "用户名 为必填项"
t('validation.required', { field: 'Username' })
```

### Language Switching

```typescript
const { changeLanguage } = useI18n();

// Change to Chinese
changeLanguage('zh');

// Change to English
changeLanguage('en');
```

### Check Current Language

```typescript
const { currentLanguage, isEnglish, isChinese } = useI18n();

if (isEnglish) {
  // Do something for English users
}
```

## Adding New Translations

1. Add the key to `locales/en.json`:
   ```json
   {
     "myFeature": {
       "title": "My Feature"
     }
   }
   ```

2. Add the same key to `locales/zh.json`:
   ```json
   {
     "myFeature": {
       "title": "我的功能"
     }
   }
   ```

3. Use in your component:
   ```typescript
   t('myFeature.title')
   ```

## Testing

Run the i18n tests:

```bash
npm test -- src/i18n/__tests__/i18n.test.ts
```

Tests cover:
- Language initialization
- Translation in both languages
- Language switching
- Interpolation
- Fallback behavior

## Best Practices

1. **Always use translation keys** - Never hardcode text
2. **Use descriptive keys** - `tools.createTool` not `button1`
3. **Group related translations** - Organize by feature
4. **Keep translations consistent** - Same term = same translation
5. **Test both languages** - Ensure UI works with different text lengths

## Components

### LanguageSwitcher

A dropdown component for switching languages:

```typescript
import { LanguageSwitcher } from '@/components/common/LanguageSwitcher';

<LanguageSwitcher />
```

### useI18n Hook

Custom hook providing i18n utilities:

```typescript
import { useI18n } from '@/hooks/useI18n';

const {
  t,              // Translation function
  i18n,           // i18next instance
  changeLanguage, // Change language function
  currentLanguage,// Current language code
  isEnglish,      // Is English selected
  isChinese,      // Is Chinese selected
} = useI18n();
```

## Language Persistence

The selected language is automatically:
- Saved to localStorage when changed
- Restored on page reload
- Used as the initial language

## Supported Languages

- **en** - English (default)
- **zh** - Chinese (中文)

## Resources

- [Full i18n Guide](../../I18N_GUIDE.md)
- [react-i18next Documentation](https://react.i18next.com/)
- [i18next Documentation](https://www.i18next.com/)
