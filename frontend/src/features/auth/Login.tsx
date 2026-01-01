import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { useToast } from '../../hooks/use-toast';
import { authService } from '../../services/authService';
import { useAuthStore } from '../../stores/authStore';

/**
 * Login Form Component
 * Requirements: 1.1, 1.2, 1.3
 * 
 * Provides user login functionality with form validation,
 * error handling, and automatic token storage.
 * 
 * WebSocket connection is automatically established by AppLayout
 * after successful login (Requirements 8.1)
 */

// Login form validation schema
const loginSchema = z.object({
  username: z.string().min(1, '用户名不能为空'),
  password: z.string().min(1, '密码不能为空'),
});

type LoginFormData = z.infer<typeof loginSchema>;

export default function Login() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const setAuth = useAuthStore((state) => state.setAuth);
  const [isLoading, setIsLoading] = useState(false);

  // Debug: Log when component mounts
  useEffect(() => {
    console.log('Login component mounted');
    console.log('Current localStorage access_token:', localStorage.getItem('access_token'));
  }, []);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormData) => {
    setIsLoading(true);

    try {
      console.log('🔐 Starting login process...');
      
      // Login and get user data
      const user = await authService.login(data);
      console.log('✓ Login successful, user:', user);
      
      // Get tokens from authService
      const accessToken = authService.getAccessToken();
      const refreshToken = authService.getRefreshToken();

      console.log('🔑 Tokens retrieved:');
      console.log('  access_token:', accessToken ? `${accessToken.substring(0, 20)}...` : 'NULL');
      console.log('  refresh_token:', refreshToken ? `${refreshToken.substring(0, 20)}...` : 'NULL');

      if (accessToken && refreshToken) {
        // Update auth store (this will also sync to localStorage)
        setAuth(user, accessToken, refreshToken);
        
        // Verify tokens are in localStorage
        console.log('✓ Auth store updated');
        console.log('  localStorage access_token:', localStorage.getItem('access_token')?.substring(0, 20) + '...');
        console.log('  localStorage refresh_token:', localStorage.getItem('refresh_token')?.substring(0, 20) + '...');

        // Show success message
        toast({
          title: '登录成功',
          description: `欢迎回来, ${user.username}!`,
        });

        // Navigate to dashboard
        console.log('🚀 Navigating to dashboard...');
        navigate('/dashboard', { replace: true });
      } else {
        throw new Error('未能获取认证令牌');
      }
    } catch (error: any) {
      console.error('❌ Login failed:', error);
      
      // Display error message
      const errorMessage = error.response?.data?.detail || error.message || '登录失败，请检查您的凭据';
      
      toast({
        title: '登录失败',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h1 className="text-2xl font-bold">登录</h1>
        <p className="text-muted-foreground mt-2">登录到您的账户</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="username">用户名</Label>
          <Input
            id="username"
            type="text"
            placeholder="输入您的用户名"
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
          <Label htmlFor="password">密码</Label>
          <Input
            id="password"
            type="password"
            placeholder="输入您的密码"
            {...register('password')}
            disabled={isLoading}
            aria-invalid={errors.password ? 'true' : 'false'}
          />
          {errors.password && (
            <p className="text-sm text-destructive" role="alert">
              {errors.password.message}
            </p>
          )}
        </div>

        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? '登录中...' : '登录'}
        </Button>
      </form>

      <div className="text-center text-sm">
        <span className="text-muted-foreground">还没有账户？</span>{' '}
        <Link to="/auth/register" className="text-primary hover:underline">
          立即注册
        </Link>
      </div>
    </div>
  );
}
