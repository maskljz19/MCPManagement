import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Brain, Lightbulb, Settings } from 'lucide-react';
import { FeasibilityAnalysis } from './FeasibilityAnalysis';
import { ImprovementSuggestions } from './ImprovementSuggestions';
import { ConfigGenerator } from './ConfigGenerator';

/**
 * AnalysisPanel Component
 * Main panel for AI analysis features
 * Provides tabs for different analysis types: feasibility, improvements, and config generation
 */
export function AnalysisPanel() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">AI 分析</h1>
        <p className="text-muted-foreground">
          使用 AI 分析工具配置、获取改进建议和生成配置
        </p>
      </div>

      <Tabs defaultValue="feasibility" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="feasibility" className="flex items-center gap-2">
            <Brain className="h-4 w-4" />
            可行性分析
          </TabsTrigger>
          <TabsTrigger value="improvements" className="flex items-center gap-2">
            <Lightbulb className="h-4 w-4" />
            改进建议
          </TabsTrigger>
          <TabsTrigger value="generate" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            配置生成
          </TabsTrigger>
        </TabsList>

        <TabsContent value="feasibility" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>可行性分析</CardTitle>
              <CardDescription>
                分析 MCP 工具配置的可行性，获取评分和建议
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FeasibilityAnalysis />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="improvements" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>改进建议</CardTitle>
              <CardDescription>
                获取现有工具的改进建议和优化方案
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ImprovementSuggestions />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="generate" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>配置生成</CardTitle>
              <CardDescription>
                根据需求自动生成 MCP 工具配置
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ConfigGenerator />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
