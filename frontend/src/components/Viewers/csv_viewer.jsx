import React, { useState, useEffect } from "react";
import Papa from "papaparse";
import Loading from "../ui/Loading";

function CSVViewer({ url }) {
  const [data, setData] = useState([]);
  const [columns, setColumns] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchDataFromUrl = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(url);
        const text = await response.text();
       
        const result = Papa.parse(text, { header: true });
        const { data, meta: { fields } } = result;
        setData(data);
        setColumns(makeColumns(fields));
      } catch (error) {
        // Error fetching CSV data
      } finally {
        setIsLoading(false);
      }
    };

    if (url) {
      fetchDataFromUrl();
    }
  }, [url]);

  const makeColumns = rawColumns => {
    return rawColumns.map(column => {
      return { Header: column, accessor: column };
    });
  };

  return (
    <div className="relative border flex flex-col rounded-sm2 overflow-hidden   max-h-[87vh] min-h-[87vh] bg-white"> 
      {isLoading ? (
        <div className="flex items-center justify-center h-full">
          <Loading padding={3} />
        </div>
      ) : data.length > 0 && columns.length > 0 ? (
        <div className="flex-1 overflow-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50 sticky top-0">
              <tr>
                {columns.map(column => (
                  <th
                    key={column.accessor}
                    className="px-6 py-3 border text-left text-xs leading-4 font-medium text-gray-500 uppercase tracking-wider"
                  >
                    {column.Header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data.map((row, rowIndex) => (
                <tr key={rowIndex} className="hover:bg-gray-50">
                  {columns.map(column => (
                    <td
                      key={column.accessor}
                      className="px-6 py-4 border whitespace-nowrap text-sm leading-5 text-gray-900"
                    >
                      {row[column.accessor] || ''}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="flex items-center justify-center h-full">
          <Loading padding={3} />
        </div>
      )}
    </div>
  );
}

export default CSVViewer;
