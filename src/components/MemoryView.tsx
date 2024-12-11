import React from 'react';
import { MemoryKV } from '../types/console';

interface MemoryViewProps {
  memoryKv: MemoryKV;
}

export const MemoryView: React.FC<MemoryViewProps> = ({ memoryKv }) => {
  return (
    <div className="content-block kv">
      <div className="content-block-title">set_memory()</div>
      <div className="content-block-body content-kv">
        {JSON.stringify(memoryKv, null, 2)}
      </div>
    </div>
  );
}; 