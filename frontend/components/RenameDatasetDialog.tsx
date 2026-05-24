'use client';

import { useState } from 'react';
import Modal from './Modal';
import { Dataset } from '@/lib/api/data';

interface RenameDatasetDialogProps {
  dataset: Dataset | null;
  onConfirm: (name: string) => void;
  onCancel: () => void;
}

export default function RenameDatasetDialog({ dataset, onConfirm, onCancel }: RenameDatasetDialogProps) {
  const [name, setName] = useState(dataset?.name || '');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim()) {
      onConfirm(name.trim());
    }
  };

  return (
    <Modal
      isOpen={!!dataset}
      onClose={onCancel}
      title="Rename Dataset"
    >
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label htmlFor="newDatasetName" className="block text-sm font-medium text-gray-700 mb-2">
            New Name
          </label>
          <input
            id="newDatasetName"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2"
            autoFocus
          />
        </div>
        <div className="flex justify-end space-x-3">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!name.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            Rename
          </button>
        </div>
      </form>
    </Modal>
  );
}
