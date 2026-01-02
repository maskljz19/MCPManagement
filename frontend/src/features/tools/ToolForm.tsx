import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { ArrowLeft, Save } from 'lucide-react';
import { apiClient } from '@/services/apiClient';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import Editor from '@monaco-editor/react';

// Form validation schema
const toolFormSchema = z.object({
  name: z.string().min(1, '名称不能为空').max(100, '名称不能超过100个字符'),
  slug: z
    .string()
    .min(1, 'Slug 不能为空')
    .max(100, 'Slug 不能超过100个字符')
    .regex(/^[a-z0-9-]+$/, 'Slug 只能包含小写字母、数字和连字符'),
  description: z.string().min(1, '描述不能为空').max(500, '描述不能超过500个字符'),
  version: z.string().min(1, '版本不能为空').regex(/^\d+\.\d+\.\d+$/, '版本格式应为 x.y.z'),
  status: z.enum(['DRAFT', 'ACTIVE', 'DEPRECATED']),
  config: z.string().min(1, '配置不能为空'),
});

type ToolFormData = z.infer<typeof toolFormSchema>;

const DEFAULT_TOOL_CONFIG = `{
  "name": "data-processor",
  "version": "1.0.0",
  "description": "Data processing MCP server",
  "server": {
    "command": "python",
    "args": ["-m", "data_processor"],
    "env": {
      "MAX_FILE_SIZE": "10MB",
      "SUPPORTED_FORMATS": "json,csv,xml"
    }
  },
  "tools": [
    {
      "name": "validate_data",
      "description": "Validate data format and structure",
      "inputSchema": {
        "type": "object",
        "properties": {
          "data": {
            "type": "string",
            "description": "Data to validate"
          },
          "format": {
            "type": "string",
            "enum": ["json", "csv", "xml"]
          }
        },
        "required": ["data", "format"]
      }
    },
    {
      "name": "convert_format",
      "description": "Convert data between formats",
      "inputSchema": {
        "type": "object",
        "properties": {
          "data": {
            "type": "string"
          },
          "from_format": {
            "type": "string",
            "enum": ["json", "csv", "xml"]
          },
          "to_format": {
            "type": "string",
            "enum": ["json", "csv", "xml"]
          }
        },
        "required": ["data", "from_format", "to_format"]
      }
    }
  ]
}`;

export default function ToolForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const isEditMode = !!id;

  const [configValue, setConfigValue] = useState(DEFAULT_TOOL_CONFIG);
  const [configError, setConfigError] = useState<string | null>(null);

  // Fetch tool data if in edit mode
  const { data: tool, isLoading } = useQuery({
    queryKey: ['tool', id],
    queryFn: () => apiClient.tools.get(id!),
    enabled: isEditMode,
  });

  // Form setup
  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<ToolFormData>({
    resolver: zodResolver(toolFormSchema),
    defaultValues: {
      name: '',
      slug: '',
      description: '',
      version: '1.0.0',
      status: 'DRAFT',
      config: DEFAULT_TOOL_CONFIG,
    },
  });

  const statusValue = watch('status');

  // Populate form with tool data in edit mode
  useEffect(() => {
    if (tool) {
      setValue('name', tool.name);
      setValue('slug', tool.slug);
      setValue('description', tool.description);
      setValue('version', tool.version);
      setValue('status', tool.status);
      const configStr = tool.config 
        ? JSON.stringify(tool.config, null, 2)
        : DEFAULT_TOOL_CONFIG;
      setValue('config', configStr);
      setConfigValue(configStr);
    }
  }, [tool, setValue]);

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: any) => apiClient.tools.create(data),
    onSuccess: (data) => {
      toast({
        title: '创建成功',
        description: '工具已成功创建。',
      });
      queryClient.invalidateQueries({ queryKey: ['tools'] });
      navigate(`/tools/${data.id}`);
    },
    onError: () => {
      toast({
        title: '创建失败',
        description: '无法创建工具，请稍后重试。',
        variant: 'destructive',
      });
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (data: any) => apiClient.tools.update(id!, data),
    onSuccess: (data) => {
      toast({
        title: '更新成功',
        description: '工具已成功更新。',
      });
      queryClient.invalidateQueries({ queryKey: ['tool', id] });
      queryClient.invalidateQueries({ queryKey: ['tools'] });
      navigate(`/tools/${data.id}`);
    },
    onError: () => {
      toast({
        title: '更新失败',
        description: '无法更新工具，请稍后重试。',
        variant: 'destructive',
      });
    },
  });

  // Handle config editor change
  const handleConfigChange = (value: string | undefined) => {
    if (!value) return;
    setConfigValue(value);
    setValue('config', value);

    // Validate JSON
    try {
      JSON.parse(value);
      setConfigError(null);
    } catch (error) {
      setConfigError('配置必须是有效的 JSON 格式');
    }
  };

  // Handle form submission
  const onSubmit = (data: ToolFormData) => {
    // Validate JSON config
    let configObj;
    try {
      configObj = JSON.parse(data.config);
    } catch (error) {
      setConfigError('配置必须是有效的 JSON 格式');
      return;
    }

    const payload = {
      name: data.name,
      slug: data.slug,
      description: data.description,
      version: data.version,
      status: data.status,
      config: configObj,
    };

    if (isEditMode) {
      updateMutation.mutate(payload);
    } else {
      createMutation.mutate(payload);
    }
  };

  // Handle back
  const handleBack = () => {
    if (isEditMode) {
      navigate(`/tools/${id}`);
    } else {
      navigate('/tools');
    }
  };

  // Auto-generate slug from name
  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const name = e.target.value;
    if (!isEditMode) {
      const slug = name
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '');
      setValue('slug', slug);
    }
  };

  if (isEditMode && isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-32" />
        <Skeleton className="h-[800px]" />
      </div>
    );
  }

  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={handleBack}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          返回
        </Button>
        <h1 className="text-3xl font-bold">
          {isEditMode ? '编辑工具' : '创建工具'}
        </h1>
        <div className="w-24" /> {/* Spacer for centering */}
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Basic Info Card */}
        <Card>
          <CardHeader>
            <CardTitle>基本信息</CardTitle>
            <CardDescription>工具的基本信息和元数据</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Name */}
            <div className="space-y-2">
              <Label htmlFor="name">
                名称 <span className="text-destructive">*</span>
              </Label>
              <Input
                id="name"
                {...register('name')}
                onChange={(e) => {
                  register('name').onChange(e);
                  handleNameChange(e);
                }}
                placeholder="输入工具名称"
              />
              {errors.name && (
                <p className="text-sm text-destructive">{errors.name.message}</p>
              )}
            </div>

            {/* Slug */}
            <div className="space-y-2">
              <Label htmlFor="slug">
                Slug <span className="text-destructive">*</span>
              </Label>
              <Input
                id="slug"
                {...register('slug')}
                placeholder="tool-slug"
                disabled={isEditMode}
              />
              {errors.slug && (
                <p className="text-sm text-destructive">{errors.slug.message}</p>
              )}
              <p className="text-xs text-muted-foreground">
                URL 友好的标识符，只能包含小写字母、数字和连字符
              </p>
            </div>

            {/* Description */}
            <div className="space-y-2">
              <Label htmlFor="description">
                描述 <span className="text-destructive">*</span>
              </Label>
              <Textarea
                id="description"
                {...register('description')}
                placeholder="输入工具描述"
                rows={3}
              />
              {errors.description && (
                <p className="text-sm text-destructive">
                  {errors.description.message}
                </p>
              )}
            </div>

            {/* Version and Status */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="version">
                  版本 <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="version"
                  {...register('version')}
                  placeholder="1.0.0"
                />
                {errors.version && (
                  <p className="text-sm text-destructive">
                    {errors.version.message}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="status">
                  状态 <span className="text-destructive">*</span>
                </Label>
                <Select
                  value={statusValue}
                  onValueChange={(value) =>
                    setValue('status', value as 'DRAFT' | 'ACTIVE' | 'DEPRECATED')
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="DRAFT">草稿</SelectItem>
                    <SelectItem value="ACTIVE">活跃</SelectItem>
                    <SelectItem value="DEPRECATED">已弃用</SelectItem>
                  </SelectContent>
                </Select>
                {errors.status && (
                  <p className="text-sm text-destructive">
                    {errors.status.message}
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Configuration Card */}
        <Card>
          <CardHeader>
            <CardTitle>配置</CardTitle>
            <CardDescription>
              工具的 JSON 配置，定义 MCP 服务器和工具。包含服务器启动命令、环境变量和工具定义（名称、描述、输入参数）。
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="border rounded-lg overflow-hidden">
                <Editor
                  height="400px"
                  defaultLanguage="json"
                  value={configValue}
                  onChange={handleConfigChange}
                  options={{
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    fontSize: 14,
                    formatOnPaste: true,
                    formatOnType: true,
                  }}
                  theme="vs-dark"
                />
              </div>
              {configError && (
                <p className="text-sm text-destructive">{configError}</p>
              )}
              {errors.config && (
                <p className="text-sm text-destructive">{errors.config.message}</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Submit Button */}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={handleBack}>
            取消
          </Button>
          <Button type="submit" disabled={isSubmitting || !!configError}>
            <Save className="mr-2 h-4 w-4" />
            {isSubmitting
              ? isEditMode
                ? '保存中...'
                : '创建中...'
              : isEditMode
              ? '保存更改'
              : '创建工具'}
          </Button>
        </div>
      </form>
    </div>
  );
}
