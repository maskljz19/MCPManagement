import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useI18n } from '@/hooks/useI18n';
import { LanguageSwitcher } from '@/components/common/LanguageSwitcher';

/**
 * I18n Demo Component
 * Demonstrates how to use internationalization in the application
 */
export function I18nDemo() {
  const { t, currentLanguage } = useI18n();

  return (
    <div className="container mx-auto p-6 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Internationalization (i18n) Demo</CardTitle>
          <CardDescription>
            This component demonstrates how to use translations in the application
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Language Switcher */}
          <div>
            <h3 className="text-lg font-semibold mb-2">Language Switcher</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Current language: <strong>{currentLanguage}</strong>
            </p>
            <LanguageSwitcher />
          </div>

          {/* Common Translations */}
          <div>
            <h3 className="text-lg font-semibold mb-2">Common Translations</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium">Loading:</p>
                <p className="text-sm text-muted-foreground">{t('common.loading')}</p>
              </div>
              <div>
                <p className="text-sm font-medium">Error:</p>
                <p className="text-sm text-muted-foreground">{t('common.error')}</p>
              </div>
              <div>
                <p className="text-sm font-medium">Success:</p>
                <p className="text-sm text-muted-foreground">{t('common.success')}</p>
              </div>
              <div>
                <p className="text-sm font-medium">Cancel:</p>
                <p className="text-sm text-muted-foreground">{t('common.cancel')}</p>
              </div>
            </div>
          </div>

          {/* Navigation Translations */}
          <div>
            <h3 className="text-lg font-semibold mb-2">Navigation Translations</h3>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm">{t('nav.dashboard')}</Button>
              <Button variant="outline" size="sm">{t('nav.tools')}</Button>
              <Button variant="outline" size="sm">{t('nav.knowledge')}</Button>
              <Button variant="outline" size="sm">{t('nav.analysis')}</Button>
              <Button variant="outline" size="sm">{t('nav.github')}</Button>
              <Button variant="outline" size="sm">{t('nav.deployments')}</Button>
              <Button variant="outline" size="sm">{t('nav.apiKeys')}</Button>
            </div>
          </div>

          {/* Auth Translations */}
          <div>
            <h3 className="text-lg font-semibold mb-2">Auth Translations</h3>
            <div className="space-y-2">
              <p className="text-sm">
                <strong>Login Title:</strong> {t('auth.loginTitle')}
              </p>
              <p className="text-sm">
                <strong>Register Title:</strong> {t('auth.registerTitle')}
              </p>
              <p className="text-sm">
                <strong>Username:</strong> {t('auth.username')}
              </p>
              <p className="text-sm">
                <strong>Password:</strong> {t('auth.password')}
              </p>
            </div>
          </div>

          {/* Error Translations */}
          <div>
            <h3 className="text-lg font-semibold mb-2">Error Translations</h3>
            <div className="space-y-2">
              <p className="text-sm text-destructive">{t('errors.generic')}</p>
              <p className="text-sm text-destructive">{t('errors.network')}</p>
              <p className="text-sm text-destructive">{t('errors.unauthorized')}</p>
              <p className="text-sm text-destructive">{t('errors.notFound')}</p>
            </div>
          </div>

          {/* Usage Instructions */}
          <div className="bg-muted p-4 rounded-lg">
            <h3 className="text-lg font-semibold mb-2">How to Use i18n</h3>
            <div className="space-y-2 text-sm">
              <p>1. Import the useI18n hook:</p>
              <code className="block bg-background p-2 rounded">
                import {'{ useI18n }'} from '@/hooks/useI18n';
              </code>
              
              <p className="mt-4">2. Use the hook in your component:</p>
              <code className="block bg-background p-2 rounded">
                const {'{ t }'} = useI18n();
              </code>
              
              <p className="mt-4">3. Translate text using the t function:</p>
              <code className="block bg-background p-2 rounded">
                {'{t(\'common.loading\')}'}
              </code>
              
              <p className="mt-4">4. Add new translations to:</p>
              <ul className="list-disc list-inside ml-4">
                <li>frontend/src/i18n/locales/en.json (English)</li>
                <li>frontend/src/i18n/locales/zh.json (Chinese)</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
