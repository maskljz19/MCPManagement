# Internationalization (i18n) Guide

This guide explains how to use internationalization in the MCP Platform Frontend application.

## Overview

The application uses `react-i18next` for internationalization, supporting multiple languages with easy switching and persistent language preferences.

## Supported Languages

- **English (en)** - Default language
- **中文 (zh)** - Chinese

## Quick Start

### Using Translations in Components

```typescript
import { useI18n } from '@/hooks/useI18n';

function MyComponent() {
  const { t } = useI18n();
  
  return (
    <div>
      <h1>{t('common.loading')}</h1>
      <button>{t('common.save')}</button>
    </div>
  );
}
```

### Using the Translation Hook

The `useI18n` hook provides several utilities:

```typescript
const {
  t,              // Translation function
  i18n,           // i18next instance
  changeLanguage, // Function to change language
  currentLanguage,// Current language code
  isEnglish,      // Boolean: is current language English
  isChinese,      // Boolean: is current language Chinese
} = useI18n();
```

### Language Switcher Component

Add the language switcher to any component:

```typescript
import { LanguageSwitcher } from '@/components/common/LanguageSwitcher';

function MyComponent() {
  return (
    <div>
      <LanguageSwitcher />
    </div>
  );
}
```

## Translation Files

Translation files are located in `frontend/src/i18n/locales/`:

- `en.json` - English translations
- `zh.json` - Chinese translations

### Translation File Structure

```json
{
  "common": {
    "loading": "Loading...",
    "error": "Error",
    "success": "Success"
  },
  "auth": {
    "login": "Login",
    "logout": "Logout"
  },
  "nav": {
    "dashboard": "Dashboard",
    "tools": "MCP Tools"
  }
}
```

## Adding New Translations

### Step 1: Add to English Translation File

Edit `frontend/src/i18n/locales/en.json`:

```json
{
  "myFeature": {
    "title": "My Feature",
    "description": "This is my feature"
  }
}
```

### Step 2: Add to Chinese Translation File

Edit `frontend/src/i18n/locales/zh.json`:

```json
{
  "myFeature": {
    "title": "我的功能",
    "description": "这是我的功能"
  }
}
```

### Step 3: Use in Component

```typescript
function MyFeature() {
  const { t } = useI18n();
  
  return (
    <div>
      <h1>{t('myFeature.title')}</h1>
      <p>{t('myFeature.description')}</p>
    </div>
  );
}
```

## Translation Categories

The translation files are organized into the following categories:

### Common
General UI elements and actions
- `common.loading`, `common.error`, `common.success`
- `common.save`, `common.cancel`, `common.delete`

### Auth
Authentication related text
- `auth.login`, `auth.logout`, `auth.register`
- `auth.username`, `auth.password`, `auth.email`

### Navigation
Navigation menu items
- `nav.dashboard`, `nav.tools`, `nav.knowledge`
- `nav.analysis`, `nav.github`, `nav.deployments`

### Dashboard
Dashboard specific text
- `dashboard.title`, `dashboard.welcome`
- `dashboard.stats.*`, `dashboard.recentActivity`

### Tools
MCP Tools management
- `tools.title`, `tools.createTool`, `tools.editTool`
- `tools.status.*`, `tools.deleteConfirm`

### Knowledge
Knowledge base related text
- `knowledge.title`, `knowledge.uploadDocument`
- `knowledge.searchDocuments`, `knowledge.semanticSearch`

### Analysis
AI Analysis features
- `analysis.title`, `analysis.feasibility`
- `analysis.improvements`, `analysis.configGenerator`

### GitHub
GitHub integration
- `github.title`, `github.connectRepository`
- `github.sync`, `github.disconnect`

### Deployments
Deployment management
- `deployments.title`, `deployments.deployTool`
- `deployments.status.*`, `deployments.health.*`

### API Keys
API key management
- `apiKeys.title`, `apiKeys.createKey`
- `apiKeys.revokeKey`, `apiKeys.keyWarning`

### Errors
Error messages
- `errors.generic`, `errors.network`, `errors.unauthorized`
- `errors.notFound`, `errors.serverError`

### Settings
Settings and preferences
- `settings.title`, `settings.language`, `settings.theme`
- `settings.languageEn`, `settings.languageZh`

### Validation
Form validation messages
- `validation.required`, `validation.minLength`
- `validation.email`, `validation.url`

## Interpolation

Use interpolation for dynamic values:

```typescript
// In translation file
{
  "validation": {
    "required": "{{field}} is required",
    "minLength": "{{field}} must be at least {{min}} characters"
  }
}

// In component
t('validation.required', { field: 'Username' })
// Output: "Username is required"

t('validation.minLength', { field: 'Password', min: 8 })
// Output: "Password must be at least 8 characters"
```

## Language Persistence

The selected language is automatically saved to `localStorage` and restored on page reload.

```typescript
// Language is saved automatically when changed
changeLanguage('zh');

// On page reload, the saved language is restored
```

## Best Practices

### 1. Always Use Translation Keys

❌ Bad:
```typescript
<button>Save</button>
```

✅ Good:
```typescript
<button>{t('common.save')}</button>
```

### 2. Use Descriptive Keys

❌ Bad:
```typescript
t('text1'), t('button2')
```

✅ Good:
```typescript
t('tools.createTool'), t('common.save')
```

### 3. Group Related Translations

❌ Bad:
```json
{
  "toolTitle": "Tools",
  "toolCreate": "Create Tool",
  "toolDelete": "Delete Tool"
}
```

✅ Good:
```json
{
  "tools": {
    "title": "Tools",
    "createTool": "Create Tool",
    "deleteTool": "Delete Tool"
  }
}
```

### 4. Keep Translations Consistent

Ensure the same term is translated consistently across the application:
- "Tool" should always be "工具" in Chinese
- "Dashboard" should always be "仪表板" in Chinese

### 5. Test Both Languages

Always test your features in both English and Chinese to ensure:
- All text is translated
- UI layout works with different text lengths
- No hardcoded text remains

## Accessibility

The language switcher is fully accessible:
- Keyboard navigable
- Screen reader friendly
- Proper ARIA labels

## Demo Component

A demo component is available at `frontend/src/components/demo/I18nDemo.tsx` that shows:
- How to use the language switcher
- Examples of common translations
- Usage instructions
- Best practices

## Configuration

The i18n configuration is in `frontend/src/i18n/config.ts`:

```typescript
i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: enTranslations },
      zh: { translation: zhTranslations },
    },
    lng: savedLanguage,
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false,
    },
  });
```

## Troubleshooting

### Translation Not Showing

1. Check if the key exists in both `en.json` and `zh.json`
2. Verify the key path is correct (e.g., `common.loading` not `loading`)
3. Ensure i18n is initialized in `main.tsx`

### Language Not Persisting

1. Check browser localStorage is enabled
2. Verify `localStorage.setItem('language', lng)` is called
3. Clear browser cache and try again

### Missing Translations

If a translation key is missing, the key itself will be displayed:
- `common.missingKey` will show as "common.missingKey"
- Add the missing key to both translation files

## Adding a New Language

To add a new language (e.g., Spanish):

1. Create `frontend/src/i18n/locales/es.json`
2. Add translations for all keys
3. Update `frontend/src/i18n/config.ts`:
   ```typescript
   import esTranslations from './locales/es.json';
   
   resources: {
     en: { translation: enTranslations },
     zh: { translation: zhTranslations },
     es: { translation: esTranslations },
   }
   ```
4. Update `LanguageSwitcher.tsx` to include the new language option

## Resources

- [react-i18next Documentation](https://react.i18next.com/)
- [i18next Documentation](https://www.i18next.com/)
- [Translation Best Practices](https://www.i18next.com/principles/fallback)
