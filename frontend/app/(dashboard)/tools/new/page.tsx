import ToolForm from "@/components/ToolForm";
import Link from "next/link";

export default function NewToolPage() {
  return (
    <div className="max-w-xl">
      <div className="mb-6">
        <Link href="/tools" className="text-sm text-gray-400 hover:text-gray-600">
          ← Tools
        </Link>
        <h1 className="text-xl font-semibold text-gray-900 mt-2">New tool</h1>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <ToolForm />
      </div>
    </div>
  );
}
