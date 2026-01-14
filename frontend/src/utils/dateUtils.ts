/**
 * 日期工具函数
 * 处理后端返回的日期格式，确保正确解析
 */

/**
 * 安全地解析日期字符串
 * 如果日期字符串缺少时区信息，自动添加 UTC 时区
 * @param dateString - 日期字符串
 * @returns Date 对象
 */
export function parseDate(dateString: string | null | undefined): Date {
  if (!dateString) {
    return new Date();
  }

  // 如果日期字符串格式为 YYYY-MM-DDTHH:mm:ss 但缺少时区信息
  // 添加 Z 后缀表示 UTC 时区
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(dateString)) {
    return new Date(dateString + 'Z');
  }

  // 否则直接解析
  return new Date(dateString);
}

/**
 * 格式化日期为本地字符串
 * @param dateString - 日期字符串
 * @returns 格式化后的日期字符串
 */
export function formatLocalDate(dateString: string | null | undefined): string {
  const date = parseDate(dateString);
  return date.toLocaleString('zh-CN');
}
