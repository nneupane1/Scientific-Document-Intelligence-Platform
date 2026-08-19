import Viewer from "@/components/Viewer/Viewer";

export default async function ViewerPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <Viewer documentId={id} />;
}
