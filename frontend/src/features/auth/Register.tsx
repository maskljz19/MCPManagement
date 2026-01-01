import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { useToast } from '../../hooks/use-toast';
import { authService } from '../../services/authService';
import { useAuthStore } from '../../stores/authStore';

/**
 * Register Form Component
 * Requirements: 1.4, 1.5
 * 
 * Provides user registration functionality with form validation,
 * error handling, and automatic login after successful registration.
 * 
 * WebSocket connection is automatically established by AppLayout
 * after successful registration and auto-login (Requirements 8.1)
 */

// Registration form validation schema
const registerSchema = z.object({
  username: z
    .string()
    .min(3, '用户名至少需要 3 个字符')
    .max(50, '用户名不能超过 50 个字符')
    .regex(/^[a-zA-Z0-9_-]+$/, '用户名只能包含字母、数字、下划线和连字符'),
  email: z
    .string()
    .min(1, '邮箱不能为空')
    .email('请输入有效的邮箱地址'),
  password: z
    .string()
    .min(8, '密码至少需要 8 个字符')
    .regex(/[A-Z]/, '密码必须包含至少一个大写字母')
    .regex(/[a-z]/, '密码必须包含至少一个小写字母')
    .regex(/[0-9]/, '密码必须包含至少一个数字'),
  confirmPassword: z.string().min(1, '请确认密码'),
  role: z.enum(['admin', 'developer', 'viewer']).optional(),
}).refine((data) => data.password === data.confirmPassword, {
  message: '两次输入的密码不一致',
  path: ['confirmPassword'],
});

type RegisterFormData = z.infer<typeof registerSchema>;

export default function Register() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { setAuth } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);
  const [selectedRole, setSelectedRole] = useState<'admin' | 'developer' | 'viewer'>('developer');

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      role: 'developer',
    },
  });

  const onSubmit = async (data: RegisterFormData) => {
    setIsLoading(true);

    try {
      // Register user (auto-login is handled by authService)
      const user = await authService.register({
        username: data.username,
        email: data.email,
        password: data.password,
        role: data.role,
      });

      // Get tokens from authService
      const accessToken = authService.getAccessToken();
      const refreshToken = authService.getRefreshToken();

      if (accessToken && refreshToken) {
        // Update auth store
        setAuth(user, accessToken, refreshToken);

        // Show success message
        toast({
          title: '注册成功',
          description: `欢迎加入, ${user.username}!`,
        });

        // Navigate to dashboard
        navigate('/dashboard', { replace: true });
      } else {
        throw new Error('注册成功但未能获取认证令牌');
      }
    } catch (error: any) {
      console.error('Registration error:', error);

      // Display error message
      let errorMessage = '注册失败，请稍后重试';
      
      if (error.response?.data?.detail) {
        if (typeof error.response.data.detail === 'string') {
          errorMessage = error.response.data.detail;
        } else if (Array.isArray(error.response.data.detail)) {
          errorMessage = error.response.data.detail.map((e: any) => e.msg).join(', ');
        }
      } else if (error.message) {
        errorMessage = error.message;
      }

      toast({
        title: '注册失败',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleRoleChange = (value: string) => {
    const role = value as 'admin' | 'developer' | 'viewer';
    setSelectedRole(role);
    setValue('role', role);
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h1 className="text-2xl font-bold">注册</h1>
        <p className="text-muted-foreground mt-2">创建新账户</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="username">用户名</Label>
          <Input
            id="username"
            type="text"
            placeholder="输入用户名"
            {...register('username')}
            disabled={isLoading}
            aria-invalid={errors.username ? 'true' : 'false'}
          />
          {errors.username && (
            <p className="text-sm text-destructive" role="alert">
              {errors.username.message}
            </p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="email">邮箱</Label>
          <Input
            id="email"
            type="email"
            placeholder="输入邮箱地址"
            {...register('email')}
            disabled={isLoading}
            aria-invalid={errors.email ? 'true' : 'false'}
          />
          {errors.email && (
            <p className="text-sm text-destructive" role="alert">
              {errors.email.message}
            </p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="password">密码</Label>
          <Input
            id="password"
            type="password"
            placeholder="输入密码"
            {...register('password')}
            disabled={isLoading}
            aria-invalid={errors.password ? 'true' : 'false'}
          />
          {errors.password && (
            <p className="text-sm text-destructive" role="alert">
              {errors.password.message}
            </p>
          )}
          <p className="text-xs text-muted-foreground">
            密码必须至少 8 个字符，包含大小写字母和数字
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="confirmPassword">确认密码</Label>
          <Input
            id="confirmPassword"
            type="password"
            placeholder="再次输入密码"
            {...register('confirmPassword')}
            disabled={isLoading}
            aria-invalid={errors.confirmPassword ? 'true' : 'false'}
          />
          {errors.confirmPassword && (
            <p className="text-sm text-destructive" role="alert">
              {errors.confirmPassword.message}
            </p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="role">角色</Label>
          <Select
            value={selectedRole}
            onValueChange={handleRoleChange}
            disabled={isLoading}
          >
            <SelectTrigger id="role">
              <SelectValue placeholder="选择角色" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="viewer">查看者</SelectItem>
              <SelectItem value="developer">开发者</SelectItem>
              <SelectItem value="admin">管理员</SelectItem>
            </SelectContent>
          </Select>
          {errors.role && (
            <p className="text-sm text-destructive" role="alert">
              {errors.role.message}
            </p>
          )}
        </div>

        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? '注册中...' : '注册'}
        </Button>
      </form>

      <div className="text-center text-sm">
        <span className="text-muted-foreground">已有账户？</span>{' '}
        <Link to="/auth/login" className="text-primary hover:underline">
          立即登录
        </Link>
      </div>
    </div>
  );
}
