import { describe, it, expect, beforeEach } from 'vitest';
import i18n from '../config';

describe('i18n Configuration', () => {
  beforeEach(() => {
    // Reset to English before each test
    i18n.changeLanguage('en');
  });

  it('should initialize with English as default language', () => {
    expect(i18n.language).toBe('en');
  });

  it('should translate common keys in English', () => {
    expect(i18n.t('common.loading')).toBe('Loading...');
    expect(i18n.t('common.error')).toBe('Error');
    expect(i18n.t('common.success')).toBe('Success');
  });

  it('should translate auth keys in English', () => {
    expect(i18n.t('auth.login')).toBe('Login');
    expect(i18n.t('auth.logout')).toBe('Logout');
    expect(i18n.t('auth.register')).toBe('Register');
  });

  it('should translate navigation keys in English', () => {
    expect(i18n.t('nav.dashboard')).toBe('Dashboard');
    expect(i18n.t('nav.tools')).toBe('MCP Tools');
    expect(i18n.t('nav.knowledge')).toBe('Knowledge Base');
  });

  it('should change language to Chinese', async () => {
    await i18n.changeLanguage('zh');
    expect(i18n.language).toBe('zh');
  });

  it('should translate common keys in Chinese', async () => {
    await i18n.changeLanguage('zh');
    expect(i18n.t('common.loading')).toBe('加载中...');
    expect(i18n.t('common.error')).toBe('错误');
    expect(i18n.t('common.success')).toBe('成功');
  });

  it('should translate auth keys in Chinese', async () => {
    await i18n.changeLanguage('zh');
    expect(i18n.t('auth.login')).toBe('登录');
    expect(i18n.t('auth.logout')).toBe('登出');
    expect(i18n.t('auth.register')).toBe('注册');
  });

  it('should translate navigation keys in Chinese', async () => {
    await i18n.changeLanguage('zh');
    expect(i18n.t('nav.dashboard')).toBe('仪表板');
    expect(i18n.t('nav.tools')).toBe('MCP 工具');
    expect(i18n.t('nav.knowledge')).toBe('知识库');
  });

  it('should fallback to English for missing translations', async () => {
    await i18n.changeLanguage('zh');
    // If a key doesn't exist, it should return the key itself
    expect(i18n.t('nonexistent.key')).toBe('nonexistent.key');
  });

  it('should support interpolation', () => {
    expect(i18n.t('validation.required', { field: 'Username' })).toBe('Username is required');
  });

  it('should support interpolation in Chinese', async () => {
    await i18n.changeLanguage('zh');
    expect(i18n.t('validation.required', { field: '用户名' })).toBe('用户名 为必填项');
  });
});
