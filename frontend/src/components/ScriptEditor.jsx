import React from 'react';
import {
  DndContext,
  closestCenter,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
  arrayMove,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  ArrowRight,
  Layers,
  Trash2,
  Plus,
  GripVertical,
} from 'lucide-react';

// ── Sortable Post Item ───────────────────────────────────────────────────────
function SortablePost({ post, idx, onRemoveReply }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: post.id.toString() });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 100 : 'auto',
    position: 'relative',
  };

  return (
    <div ref={setNodeRef} style={style} className={`post-item ${isDragging ? 'dragging' : ''}`}>
      <div className="post-header">
        <span className="post-id">Reply &gt;&gt;{post.id}</span>
        <button
          className="icon-button drag-handle"
          {...attributes}
          {...listeners}
          title="Drag to reorder"
        >
          <GripVertical size={14} />
        </button>
      </div>
      <div className="post-text">{post.text}</div>
      <div className="post-actions">
        <button
          className="icon-button delete"
          onClick={() => onRemoveReply(idx)}
          title="Remove"
        >
          <Trash2 size={16} /> Remove
        </button>
      </div>
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────────────────────
export default function ScriptEditor({
  selectedThread,
  selectedBoard,
  playlist,
  currentOtherReplies,
  otherRepliesCount,
  page,
  totalPages,
  onRemoveReply,
  onAddReply,
  onReorder,
  onSetPage,
  onProceed,
}) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor)
  );

  const op = playlist[0];
  const replies = playlist.slice(1);

  const handleDragEnd = event => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = replies.findIndex(p => p.id.toString() === active.id);
    const newIndex = replies.findIndex(p => p.id.toString() === over.id);
    if (oldIndex === -1 || newIndex === -1) return;

    onReorder(arrayMove(replies, oldIndex, newIndex));
  };

  return (
    <div className="step-container full animate-fade-in" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="section-header">
        <div className="section-title">
          <h2 className="text-gradient">Review Script</h2>
          <p>Thread {selectedThread} from /{selectedBoard}/</p>
        </div>
        <button className="btn-primary" onClick={onProceed}>
          Proceed to Render <ArrowRight size={16} />
        </button>
      </div>

      <div className="review-layout">
        {/* Left Panel: Current Script */}
        <div className="review-panel">
          <div className="panel-header">
            <div className="flex-center gap-1">
              <Layers size={18} color="var(--accent-secondary)" />
              <h2>Current Script ({playlist.length})</h2>
            </div>
            <span className="text-muted" style={{ fontSize: '0.75rem' }}>
              Drag replies to reorder
            </span>
          </div>
          <div className="panel-body">
            {/* OP — always first, not draggable */}
            {op && (
              <div className="post-item op-post">
                <div className="post-header">
                  <span className="post-id">OP</span>
                  <span className="text-muted" style={{ fontSize: '0.72rem' }}>pinned</span>
                </div>
                <div className="post-text">{op.text}</div>
              </div>
            )}

            {/* Replies — draggable */}
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragEnd={handleDragEnd}
            >
              <SortableContext
                items={replies.map(p => p.id.toString())}
                strategy={verticalListSortingStrategy}
              >
                {replies.map((post, idx) => (
                  <SortablePost
                    key={post.id}
                    post={post}
                    idx={idx + 1}
                    onRemoveReply={onRemoveReply}
                  />
                ))}
              </SortableContext>
            </DndContext>
          </div>
        </div>

        {/* Right Panel: Other Replies */}
        <div className="review-panel">
          <div className="panel-header">
            <h2>Other Replies ({otherRepliesCount})</h2>
          </div>
          <div className="panel-body">
            {currentOtherReplies.length > 0 ? (
              currentOtherReplies.map(post => (
                <div key={post.id} className="post-item">
                  <div className="post-header">
                    <span className="post-id">Reply &gt;&gt;{post.id}</span>
                  </div>
                  <div className="post-text">{post.text}</div>
                  <div className="post-actions">
                    <button
                      className="icon-button add"
                      onClick={() => onAddReply(post)}
                      title="Add to Script"
                    >
                      <Plus size={16} /> Add
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-state">No more replies.</div>
            )}

            {totalPages > 1 && (
              <div className="pagination">
                <button disabled={page === 1} onClick={() => onSetPage(page - 1)}>
                  ←
                </button>
                <span>
                  {page} / {totalPages}
                </span>
                <button disabled={page === totalPages} onClick={() => onSetPage(page + 1)}>
                  →
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
