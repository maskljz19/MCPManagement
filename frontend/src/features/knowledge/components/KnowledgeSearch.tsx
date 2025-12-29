import { useState } from 'react';
import { Search, Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { SearchResult } from '@/types';

interface KnowledgeSearchProps {
  onResultClick?: (documentId: string) => void;
  onSearch: (query: string) => Promise<void>;
  results: SearchResult[];
  isLoading: boolean;
}

export default function KnowledgeSearch({
  onResultClick,
  onSearch,
  results,
  isLoading,
}: KnowledgeSearchProps) {
  const [query, setQuery] = useState('');

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      await onSearch(query);
    }
  };

  const handleResultClick = (documentId: string) => {
    if (onResultClick) {
      onResultClick(documentId);
    }
  };

  return (
    <div className="space-y-6">
      {/* Search Input */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="text"
            placeholder="搜索文档..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <Button type="submit" disabled={isLoading || !query.trim()}>
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              搜索中...
            </>
          ) : (
            '搜索'
          )}
        </Button>
      </form>

      {/* Search Results */}
      {results.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">搜索结果</h3>
            <span className="text-sm text-muted-foreground">
              找到 {results.length} 个结果
            </span>
          </div>

          <div className="space-y-3">
            {results.map((result) => (
              <Card
                key={result.document_id}
                className="cursor-pointer hover:bg-accent transition-colors"
                onClick={() => handleResultClick(result.document_id)}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <CardTitle className="text-base">{result.title}</CardTitle>
                    <Badge variant="secondary" className="ml-2">
                      {(result.similarity_score * 100).toFixed(1)}% 匹配
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <CardDescription className="line-clamp-2">
                    {result.content}
                  </CardDescription>
                  {result.metadata?.tags && result.metadata.tags.length > 0 && (
                    <div className="flex gap-2 mt-3">
                      {result.metadata.tags.map((tag: string, index: number) => (
                        <Badge key={index} variant="outline" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* No Results */}
      {!isLoading && results.length === 0 && query && (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-muted-foreground">未找到匹配的文档</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
