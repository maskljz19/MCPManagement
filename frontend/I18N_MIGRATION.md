# i18n Migration Guide

This guide helps developers migrate existing components to use internationalization.

## Quick Migration Checklist

- [ ] Import `useI18n` hook
- [ ] Replace hardcoded text with `t()` calls
- [ ] Add missing translation keys to both `en.json` and `zh.json`
- [ ] Test component in both languages
- [ ] Verify UI layout works with different text lengths

## Step-by-Step Migration

### Step 1: Import the Hook

Add the import at the top of your component:

```typescript
import { useI18n } from '@/hooks/useI18n';
```

### Step 2: Use the Hook

Add the hook call inside your component:

```typescript
function MyComponent() {
  const { t } = useI18n();
  
  // ... rest of component
}
```

### Step 3: Replace Hardcoded Text

#### Before:
```typescript
<Button>Save</Button>
<h1>Dashboard</h1>
<p>Loading...</p>
```

#### After:
```typescript
<Button>{t('common.save')}</Button>
<h1>{t('nav.dashboard')}</h1>
<p>{t('common.loading')}</p>
```

### Step 4: Add Missing Translations

If a translation key doesn't exist, add it to both files:

**en.json:**
```json
{
  "myFeature": {
    "title": "My Feature",
    "description": "This is my feature"
  }
}
```

**zh.json:**
```json
{
  "myFeature": {
    "title": "我的功能",
    "description": "这是我的功能"
  }
}
```

## Common Migration Patterns

### Pattern 1: Simple Text

```typescript
// Before
<h1>MCP Tools</h1>

// After
<h1>{t('tools.title')}</h1>
```

### Pattern 2: Button Labels

```typescript
// Before
<Button>Create Tool</Button>
<Button>Delete</Button>
<Button>Cancel</Button>

// After
<Button>{t('tools.createTool')}</Button>
<Button>{t('common.delete')}</Button>
<Button>{t('common.cancel')}</Button>
```

### Pattern 3: Form Labels

```typescript
// Before
<Label>Username</Label>
<Label>Password</Label>
<Label>Email</Label>

// After
<Label>{t('auth.username')}</Label>
<Label>{t('auth.password')}</Label>
<Label>{t('auth.email')}</Label>
```

### Pattern 4: Error Messages

```typescript
// Before
<p className="text-destructive">An error occurred</p>

// After
<p className="text-destructive">{t('errors.generic')}</p>
```

### Pattern 5: Status Text

```typescript
// Before
const statusText = status === 'active' ? 'Active' : 'Inactive';

// After
const statusText = status === 'active' 
  ? t('tools.status.active') 
  : t('tools.status.inactive');
```

### Pattern 6: Conditional Text

```typescript
// Before
<p>{isLoading ? 'Loading...' : 'Ready'}</p>

// After
<p>{isLoading ? t('common.loading') : t('common.ready')}</p>
```

### Pattern 7: Interpolation

```typescript
// Before
<p>Welcome back, {username}!</p>

// After
// First add to translations:
// en.json: "welcome": "Welcome back, {{username}}!"
// zh.json: "welcome": "欢迎回来，{{username}}！"

<p>{t('dashboard.welcome', { username })}</p>
```

### Pattern 8: Pluralization

```typescript
// Before
<p>{count} tool{count !== 1 ? 's' : ''}</p>

// After
// Add to translations:
// en.json: "toolCount": "{{count}} tool",
//          "toolCount_plural": "{{count}} tools"
// zh.json: "toolCount": "{{count}} 个工具"

<p>{t('tools.toolCount', { count })}</p>
```

### Pattern 9: ARIA Labels

```typescript
// Before
<Button aria-label="Close dialog">
  <X />
</Button>

// After
<Button aria-label={t('common.close')}>
  <X />
</Button>
```

### Pattern 10: Placeholder Text

```typescript
// Before
<Input placeholder="Search tools..." />

// After
<Input placeholder={t('tools.searchTools')} />
```

## Component Examples

### Example 1: Login Form

#### Before:
```typescript
function LoginForm() {
  return (
    <form>
      <h1>Sign in to your account</h1>
      <Label>Username</Label>
      <Input />
      <Label>Password</Label>
      <Input type="password" />
      <Button>Login</Button>
    </form>
  );
}
```

#### After:
```typescript
import { useI18n } from '@/hooks/useI18n';

function LoginForm() {
  const { t } = useI18n();
  
  return (
    <form>
      <h1>{t('auth.loginTitle')}</h1>
      <Label>{t('auth.username')}</Label>
      <Input />
      <Label>{t('auth.password')}</Label>
      <Input type="password" />
      <Button>{t('auth.login')}</Button>
    </form>
  );
}
```

### Example 2: Tool Card

#### Before:
```typescript
function ToolCard({ tool }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{tool.name}</CardTitle>
        <Badge>{tool.status}</Badge>
      </CardHeader>
      <CardContent>
        <p>{tool.description}</p>
        <Button>View Details</Button>
        <Button>Edit</Button>
        <Button>Delete</Button>
      </CardContent>
    </Card>
  );
}
```

#### After:
```typescript
import { useI18n } from '@/hooks/useI18n';

function ToolCard({ tool }) {
  const { t } = useI18n();
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>{tool.name}</CardTitle>
        <Badge>{t(`tools.status.${tool.status}`)}</Badge>
      </CardHeader>
      <CardContent>
        <p>{tool.description}</p>
        <Button>{t('common.view')}</Button>
        <Button>{t('common.edit')}</Button>
        <Button>{t('common.delete')}</Button>
      </CardContent>
    </Card>
  );
}
```

### Example 3: Confirmation Dialog

#### Before:
```typescript
function DeleteDialog({ onConfirm }) {
  return (
    <AlertDialog>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Are you sure?</AlertDialogTitle>
          <AlertDialogDescription>
            This action cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm}>
            Delete
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

#### After:
```typescript
import { useI18n } from '@/hooks/useI18n';

function DeleteDialog({ onConfirm }) {
  const { t } = useI18n();
  
  return (
    <AlertDialog>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t('common.confirm')}</AlertDialogTitle>
          <AlertDialogDescription>
            {t('tools.deleteConfirm')}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm}>
            {t('common.delete')}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

## Testing After Migration

### 1. Visual Testing

Switch between languages and verify:
- All text is translated
- UI layout doesn't break with longer/shorter text
- No text overflow issues
- Proper text alignment

### 2. Functional Testing

Ensure:
- All features work in both languages
- Form validation messages are translated
- Error messages are translated
- Success messages are translated

### 3. Accessibility Testing

Verify:
- ARIA labels are translated
- Screen reader announcements work in both languages
- Keyboard navigation still works

## Common Issues and Solutions

### Issue 1: Missing Translation Key

**Problem:** Text shows as "common.missingKey" instead of translated text

**Solution:** Add the key to both `en.json` and `zh.json`

### Issue 2: Text Overflow

**Problem:** Chinese text is longer and breaks the layout

**Solution:** Use CSS to handle overflow:
```css
.text-container {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

### Issue 3: Interpolation Not Working

**Problem:** `{{username}}` shows literally instead of the value

**Solution:** Ensure the translation file has the placeholder:
```json
{
  "welcome": "Welcome, {{username}}!"
}
```

### Issue 4: Language Not Persisting

**Problem:** Language resets to English on page reload

**Solution:** Ensure `changeLanguage` is called, which saves to localStorage:
```typescript
const { changeLanguage } = useI18n();
changeLanguage('zh'); // This saves to localStorage
```

## Migration Priority

Migrate components in this order:

1. **High Priority** (User-facing text):
   - Authentication pages
   - Navigation menus
   - Error messages
   - Form labels and validation

2. **Medium Priority**:
   - Dashboard
   - Tool management
   - Deployment pages
   - Settings

3. **Low Priority**:
   - Demo components
   - Development tools
   - Internal utilities

## Verification Checklist

After migrating a component:

- [ ] All visible text uses `t()` function
- [ ] No hardcoded strings remain
- [ ] Translation keys exist in both `en.json` and `zh.json`
- [ ] Component renders correctly in English
- [ ] Component renders correctly in Chinese
- [ ] Layout doesn't break with different text lengths
- [ ] ARIA labels are translated
- [ ] Form validation messages are translated
- [ ] Error messages are translated
- [ ] Tests pass in both languages

## Getting Help

- Check the [i18n Guide](./I18N_GUIDE.md) for detailed documentation
- Review the [i18n Demo Component](./src/components/demo/I18nDemo.tsx) for examples
- Look at migrated components like `Header.tsx` and `Sidebar.tsx` for reference
- Run tests: `npm test -- src/i18n/__tests__/i18n.test.ts`

## Resources

- [react-i18next Documentation](https://react.i18next.com/)
- [i18next Documentation](https://www.i18next.com/)
- [Translation Best Practices](https://www.i18next.com/principles/fallback)
