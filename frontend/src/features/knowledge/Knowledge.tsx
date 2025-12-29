import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';
import apiClient from '@/services/apiClient';
import KnowledgeSearch from './components/KnowledgeSearch';
import DocumentList from './components/DocumentList';
import DocumentUpload from './components/DocumentUpload';
import DocumentViewer from './components/DocumentViewer';
import DeleteDocumentDialog from './components/DeleteDocumentDialog';
import type { SearchResult } from '@/types';

export default function Knowledge() {
  const { toast } = useToast();
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false);
  const [deleteDocumentId, setDeleteDocumentId] = useState<string | null>(null);
  const [deleteDocumentTitle, setDeleteDocumentTitle] = useState<string>('');

  // Fetch all documents
  const { data: documentsData, isLoading: isLoadingDocuments } = useQuery({
    queryKey: ['documents'],
    queryFn: () => apiClient.knowledge.listDocuments(),
  });

  const documents = documentsData?.items || [];

  // Handle search
  const handleSearch = async (query: string) => {
    setIsSearching(true);
    try {
      const results = await apiClient.knowledge.search({ query, limit: 10 });
      setSearchResults(results.results);
    } catch (error) {
      toast({
        title: '搜索失败',
        description: '无法执行搜索，请稍后重试',
        variant: 'destructive',
      });
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  // Handle document click from search results or list
  const handleDocumentClick = (documentId: string) => {
    setSelectedDocumentId(documentId);
  };

  // Handle delete click
  const handleDeleteClick = (documentId: string) => {
    const doc = documents.find((d) => d.document_id === documentId);
    setDeleteDocumentId(documentId);
    setDeleteDocumentTitle(doc?.title || '');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">知识库</h1>
          <p className="text-muted-foreground mt-1">
            上传文档并使用语义搜索查询知识库
          </p>
        </div>
        <Button onClick={() => setIsUploadDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          上传文档
        </Button>
      </div>

      {/* Upload Dialog */}
      <DocumentUpload
        open={isUploadDialogOpen}
        onOpenChange={setIsUploadDialogOpen}
      />

      {/* Document Viewer */}
      <DocumentViewer
        documentId={selectedDocumentId}
        open={!!selectedDocumentId}
        onOpenChange={(open) => !open && setSelectedDocumentId(null)}
      />

      {/* Delete Confirmation Dialog */}
      <DeleteDocumentDialog
        documentId={deleteDocumentId}
        documentTitle={deleteDocumentTitle}
        open={!!deleteDocumentId}
        onOpenChange={(open) => !open && setDeleteDocumentId(null)}
      />

      {/* Tabs */}
      <Tabs defaultValue="search" className="space-y-6">
        <TabsList>
          <TabsTrigger value="search">搜索</TabsTrigger>
          <TabsTrigger value="documents">所有文档</TabsTrigger>
        </TabsList>

        {/* Search Tab */}
        <TabsContent value="search" className="space-y-6">
          <KnowledgeSearch
            onSearch={handleSearch}
            onResultClick={handleDocumentClick}
            results={searchResults}
            isLoading={isSearching}
          />
        </TabsContent>

        {/* Documents Tab */}
        <TabsContent value="documents" className="space-y-6">
          <DocumentList
            documents={documents}
            onDocumentClick={handleDocumentClick}
            onDeleteClick={handleDeleteClick}
            isLoading={isLoadingDocuments}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
