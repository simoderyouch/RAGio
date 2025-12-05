import React, { useState, useEffect } from "react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github.css';
import Loading from "../ui/Loading";

function MdViewer({ url }) {
  const [content, setContent] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchDataFromUrl = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(url);
        const text = await response.text();
        setContent(text);
      } catch (error) {
        setContent("Error loading file content.");
      } finally {
        setIsLoading(false);
      }
    };

    if (url) {
      fetchDataFromUrl();
    }
  }, [url]);

  return (
    <div className="relative border flex flex-col rounded-sm2 overflow-hidden  max-h-[87vh] min-h-[87vh] bg-white">
      {isLoading ? (
        <div className="flex items-center justify-center h-full">
          <Loading padding={3} />
        </div>
      ) : (
        <div className="flex-1 overflow-auto p-6">
          <div className="prose prose-sm md:prose-base lg:prose-lg max-w-none 
            prose-headings:font-bold prose-headings:text-gray-900
            prose-h1:text-3xl prose-h1:border-b prose-h1:border-gray-200 prose-h1:pb-2 prose-h1:mb-4
            prose-h2:text-2xl prose-h2:mt-6 prose-h2:mb-3
            prose-h3:text-xl prose-h3:mt-4 prose-h3:mb-2
            prose-p:text-gray-700 prose-p:leading-relaxed
            prose-a:text-primary prose-a:no-underline hover:prose-a:underline
            prose-strong:text-gray-900 prose-strong:font-semibold
            prose-em:text-gray-700 prose-em:italic
            prose-code:text-sm prose-code:bg-gray-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:font-mono prose-code:text-gray-800
            prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-pre:rounded-lg prose-pre:p-4 prose-pre:overflow-x-auto
            prose-pre_code:bg-transparent prose-pre_code:text-gray-100 prose-pre_code:p-0
            prose-blockquote:border-l-4 prose-blockquote:border-gray-300 prose-blockquote:pl-4 prose-blockquote:italic prose-blockquote:text-gray-600
            prose-ul:list-disc prose-ul:pl-6 prose-ul:my-4
            prose-ol:list-decimal prose-ol:pl-6 prose-ol:my-4
            prose-li:my-2 prose-li:text-gray-700
            prose-table:w-full prose-table:border-collapse prose-table:my-4
            prose-th:border prose-th:border-gray-300 prose-th:bg-gray-50 prose-th:px-4 prose-th:py-2 prose-th:text-left prose-th:font-semibold prose-th:text-gray-900
            prose-td:border prose-td:border-gray-300 prose-td:px-4 prose-td:py-2 prose-td:text-gray-700
            prose-hr:border-gray-300 prose-hr:my-6
            prose-img:rounded-lg prose-img:shadow-md prose-img:my-4">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeHighlight]}
              components={{
                code({ inline, className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '');
                  return !inline && match ? (
                    <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto my-4">
                      <code className={className} {...props}>
                        {children}
                      </code>
                    </pre>
                  ) : (
                    <code className="bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded text-sm font-mono" {...props}>
                      {children}
                    </code>
                  );
                },
                table({ children }) {
                  return (
                    <div className="overflow-x-auto my-4">
                      <table className="min-w-full border-collapse border border-gray-300">
                        {children}
                      </table>
                    </div>
                  );
                },
                a({ href, children }) {
                  return (
                    <a 
                      href={href} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-primary hover:underline"
                    >
                      {children}
                    </a>
                  );
                }
              }}
            >
              {content}
            </ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}

export default MdViewer;

