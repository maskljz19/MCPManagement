import { useTranslation } from 'react-i18next';

/**
 * Custom hook for internationalization
 * Provides translation function and language utilities
 */
export function useI18n() {
  const { t, i18n } = useTranslation();

  const changeLanguage = (lng: string) => {
    i18n.changeLanguage(lng);
    localStorage.setItem('language', lng);
  };

  const currentLanguage = i18n.language;
  const isEnglish = currentLanguage === 'en';
  const isChinese = currentLanguage === 'zh';

  return {
    t,
    i18n,
    changeLanguage,
    currentLanguage,
    isEnglish,
    isChinese,
  };
}
