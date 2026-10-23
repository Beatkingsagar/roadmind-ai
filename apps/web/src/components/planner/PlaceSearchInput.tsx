import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Search, MapPin, X, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { api } from '../../api/client';
import type { PlaceSearchResult, RealPlace } from '../../api/types';

interface PlaceSearchInputProps {
  id: string;
  label: string;
  placeholder?: string;
  selectedPlace: RealPlace | null;
  onSelectPlace: (place: RealPlace | null) => void;
  accentColor?: string;
  badgeLabel?: string;
  exampleSuggestions?: string[];
}

export const PlaceSearchInput: React.FC<PlaceSearchInputProps> = ({
  id,
  label,
  placeholder = 'Search place (e.g., Kundapura, Mangaluru)...',
  selectedPlace,
  onSelectPlace,
  accentColor = 'var(--primary-500)',
  badgeLabel,
  exampleSuggestions = ['Kundapura', 'Mangaluru', 'Udupi'],
}) => {
  const [inputValue, setInputValue] = useState<string>(selectedPlace ? selectedPlace.displayName : '');
  const [results, setResults] = useState<PlaceSearchResult[]>([]);
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [highlightedIndex, setHighlightedIndex] = useState<number>(-1);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync internal input text when selectedPlace changes externally (e.g., on swap or clear)
  useEffect(() => {
    if (selectedPlace) {
      setInputValue(selectedPlace.displayName);
    } else {
      setInputValue('');
    }
  }, [selectedPlace]);

  // Handle outside click to close dropdown
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Debounced search query
  const executeSearch = useCallback(async (query: string) => {
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setResults([]);
      setIsLoading(false);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await api.searchPlaces(trimmed);
      setResults(response.results);
      setIsOpen(true);
      setHighlightedIndex(response.results.length > 0 ? 0 : -1);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Geocoding search failed';
      setError(msg);
      setResults([]);
      setIsOpen(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setInputValue(val);

    // If text was modified after selecting a place, invalidate the selected place
    // until the user explicitly selects a valid option from the dropdown
    if (selectedPlace && val !== selectedPlace.displayName) {
      onSelectPlace(null);
    }

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    if (val.trim().length >= 2) {
      setIsLoading(true);
      debounceTimerRef.current = setTimeout(() => {
        executeSearch(val);
      }, 300);
    } else {
      setResults([]);
      setIsOpen(false);
      setIsLoading(false);
    }
  };

  const handleSelectResult = (result: PlaceSearchResult) => {
    const place: RealPlace = {
      id: result.id,
      name: result.name,
      displayName: result.display_name,
      lat: result.lat,
      lon: result.lon,
      source: result.source,
      category: result.category,
    };
    onSelectPlace(place);
    setInputValue(result.display_name);
    setIsOpen(false);
    setResults([]);
    setError(null);
  };

  const handleClear = () => {
    setInputValue('');
    onSelectPlace(null);
    setResults([]);
    setIsOpen(false);
    setError(null);
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInputValue(suggestion);
    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    executeSearch(suggestion);
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen) {
      if (e.key === 'ArrowDown' && results.length > 0) {
        setIsOpen(true);
      }
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev < results.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : results.length - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (highlightedIndex >= 0 && highlightedIndex < results.length) {
        handleSelectResult(results[highlightedIndex]);
      }
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  const isConfirmed = !!selectedPlace;

  return (
    <div ref={containerRef} className="place-search-container" style={{ position: 'relative', width: '100%' }}>
      {/* Label and Status */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
        <label
          htmlFor={id}
          className="input-label"
          style={{ display: 'flex', alignItems: 'center', gap: '6px', margin: 0, fontWeight: 600 }}
        >
          <span
            style={{
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              background: accentColor,
              display: 'inline-block',
              boxShadow: `0 0 6px ${accentColor}`,
            }}
          />
          <span>{label}</span>
          {badgeLabel && (
            <span
              style={{
                fontSize: '10px',
                padding: '1px 5px',
                borderRadius: '4px',
                background: 'var(--bg-tertiary)',
                color: 'var(--text-muted)',
                fontWeight: 700,
              }}
            >
              {badgeLabel}
            </span>
          )}
        </label>

        {isConfirmed ? (
          <span
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '11px',
              color: 'var(--status-emerald)',
              fontWeight: 600,
            }}
          >
            <CheckCircle2 size={13} />
            <span>Validated ({selectedPlace.lat.toFixed(4)}, {selectedPlace.lon.toFixed(4)})</span>
          </span>
        ) : inputValue.trim().length >= 2 ? (
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            Select from suggestions
          </span>
        ) : null}
      </div>

      {/* Input Field with search icon and clear button */}
      <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
        <span
          style={{
            position: 'absolute',
            left: '12px',
            color: isConfirmed ? accentColor : 'var(--text-muted)',
            display: 'flex',
            alignItems: 'center',
            pointerEvents: 'none',
          }}
        >
          {isLoading ? (
            <Loader2 size={16} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
          ) : (
            <Search size={16} />
          )}
        </span>

        <input
          ref={inputRef}
          id={id}
          type="text"
          className="input-text"
          placeholder={placeholder}
          value={inputValue}
          onChange={handleInputChange}
          onFocus={() => {
            if (results.length > 0) setIsOpen(true);
          }}
          onKeyDown={handleKeyDown}
          autoComplete="off"
          style={{
            paddingLeft: '36px',
            paddingRight: inputValue ? '36px' : '12px',
            borderColor: isConfirmed ? accentColor : undefined,
            boxShadow: isConfirmed ? `0 0 0 1px ${accentColor}20` : undefined,
          }}
        />

        {inputValue && (
          <button
            type="button"
            onClick={handleClear}
            className="btn btn-ghost btn-icon"
            title="Clear search"
            style={{
              position: 'absolute',
              right: '8px',
              padding: '4px',
              borderRadius: '50%',
              color: 'var(--text-muted)',
            }}
          >
            <X size={15} />
          </button>
        )}
      </div>

      {/* Quick Suggestion Chips */}
      {!selectedPlace && exampleSuggestions.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '6px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Try:</span>
          {exampleSuggestions.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => handleSuggestionClick(item)}
              style={{
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '12px',
                padding: '2px 8px',
                fontSize: '11px',
                color: 'var(--primary-400)',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--bg-surface-hover)';
                e.currentTarget.style.borderColor = 'var(--primary-500)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'var(--bg-tertiary)';
                e.currentTarget.style.borderColor = 'var(--border-subtle)';
              }}
            >
              {item}
            </button>
          ))}
        </div>
      )}

      {/* Dropdown Results */}
      {isOpen && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 4px)',
            left: 0,
            right: 0,
            zIndex: 1100,
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-medium)',
            borderRadius: 'var(--radius-md)',
            boxShadow: 'var(--shadow-xl)',
            maxHeight: '280px',
            overflowY: 'auto',
          }}
        >
          {error && (
            <div
              style={{
                padding: '12px 14px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                color: 'var(--status-amber)',
                fontSize: '12px',
                background: 'var(--status-amber-bg)',
              }}
            >
              <AlertCircle size={15} />
              <span>{error}</span>
            </div>
          )}

          {!error && results.length === 0 && !isLoading && (
            <div style={{ padding: '14px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
              No real-world locations found for "{inputValue}".
            </div>
          )}

          {!error &&
            results.map((result, idx) => {
              const isHighlighted = idx === highlightedIndex;
              const isCache = result.source === 'verified_cache';

              return (
                <div
                  key={result.id}
                  onClick={() => handleSelectResult(result)}
                  onMouseEnter={() => setHighlightedIndex(idx)}
                  style={{
                    padding: '10px 14px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '10px',
                    borderBottom: idx < results.length - 1 ? '1px solid var(--border-subtle)' : 'none',
                    background: isHighlighted ? 'var(--bg-tertiary)' : 'transparent',
                    transition: 'background 0.1s ease',
                  }}
                >
                  <MapPin
                    size={16}
                    color={isCache ? 'var(--primary-500)' : 'var(--text-muted)'}
                    style={{ marginTop: '2px', flexShrink: 0 }}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '2px' }}>
                      <strong style={{ fontSize: '13px', color: 'var(--text-primary)' }}>{result.name}</strong>
                      <span
                        style={{
                          fontSize: '10px',
                          padding: '1px 6px',
                          borderRadius: '4px',
                          fontWeight: 700,
                          background: isCache ? 'rgba(14, 165, 233, 0.15)' : 'var(--bg-tertiary)',
                          color: isCache ? 'var(--primary-400)' : 'var(--text-muted)',
                          border: isCache ? '1px solid rgba(14, 165, 233, 0.3)' : '1px solid var(--border-subtle)',
                        }}
                      >
                        {isCache ? 'Verified Cache' : 'OSM Geocoded'}
                      </span>
                    </div>
                    <div
                      style={{
                        fontSize: '11px',
                        color: 'var(--text-secondary)',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        marginBottom: '4px',
                      }}
                    >
                      {result.display_name}
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                      Coordinates: <code>{result.lat.toFixed(4)}° N, {result.lon.toFixed(4)}° E</code>
                    </div>
                  </div>
                </div>
              );
            })}
        </div>
      )}
    </div>
  );
};
