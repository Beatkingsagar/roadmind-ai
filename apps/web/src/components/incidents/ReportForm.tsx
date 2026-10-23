import React, { useState, useEffect } from 'react';
import { Send, Upload, CheckCircle, AlertTriangle, FileText } from 'lucide-react';
import { api, ApiError } from '../../api/client';
import type { RoadSegmentResponse } from '../../api/types';
import { useReplay } from '../../context/ReplayContext';

export const ReportForm: React.FC<{ onSuccess?: () => void }> = ({ onSuccess }) => {
  const { replayTime } = useReplay();
  const [segments, setSegments] = useState<RoadSegmentResponse[]>([]);
  const [segmentId, setSegmentId] = useState<string>('seg_corridor_e');
  const [incidentType, setIncidentType] = useState<string>('accident');
  const [severity, setSeverity] = useState<string>('high');
  const [description, setDescription] = useState<string>('Multi-vehicle collision blocking two lanes with emergency responders on site.');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [submitting, setSubmitting] = useState<boolean>(false);
  const [successInfo, setSuccessInfo] = useState<{ reportId: string; confidence: number } | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    api.getSegments()
      .then((segs) => {
        if (mounted) {
          setSegments(segs);
          if (segs.length > 0 && !segs.some((s) => s.id === segmentId)) {
            setSegmentId(segs[0].id);
          }
        }
      })
      .catch((err) => console.error('Failed to load segments for reporting:', err));
    return () => {
      mounted = false;
    };
  }, [segmentId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!segmentId) {
      setErrorMessage('Please select an affected road segment.');
      return;
    }
    if (!description.trim()) {
      setErrorMessage('Please provide a description of the incident.');
      return;
    }

    setSubmitting(true);
    setErrorMessage(null);
    setSuccessInfo(null);

    try {
      const nowIso = replayTime || new Date().toISOString();
      const matchedSeg = segments.find((s) => s.id === segmentId);
      const coords = matchedSeg?.coordinates?.[0] || [40.75, -73.98];
      const reportRes = await api.createReport({
        segment_id: segmentId,
        incident_type: (incidentType as any),
        claimed_event_time: nowIso,
        location_description: matchedSeg?.name || `Segment ${segmentId}`,
        latitude: coords[0],
        longitude: coords[1],
        reporter_reference: 'citizen_mobile_app',
        description: `[Severity: ${severity.toUpperCase()}] ${description.trim()}`,
      });

      // If a file was selected, upload it as evidence to the created report
      if (selectedFile && reportRes.id) {
        try {
          await api.uploadEvidence(reportRes.id, selectedFile, {
            claim: 'Citizen uploaded scene photo',
            uploaded_at: nowIso,
          });
        } catch (uploadErr) {
          console.warn('Evidence upload warning:', uploadErr);
        }
      }

      setSuccessInfo({
        reportId: reportRes.id,
        confidence: 0.85,
      });
      setSelectedFile(null);
      if (onSuccess) onSuccess();
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to submit incident report. Please check backend connection.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card" style={{ maxWidth: '640px', margin: '0 auto' }}>
      <div className="card-header">
        <div>
          <div className="card-title">
            <AlertTriangle size={18} color="var(--status-amber)" />
            <span>Citizen Incident & Road Hazard Report</span>
          </div>
          <div className="card-subtitle">
            Submit verified eyewitness or sensor reports with optional photo evidence
          </div>
        </div>
      </div>

      {successInfo && (
        <div className="alert alert-success" style={{ marginBottom: '16px' }}>
          <CheckCircle size={18} />
          <div>
            <strong>Report successfully ingested into traffic intelligence engine!</strong>
            <div style={{ fontSize: '12px', marginTop: '4px' }}>
              Report ID: <code>{successInfo.reportId}</code> &bull; Initial Confidence Score: <strong>{Math.round(successInfo.confidence * 100)}%</strong>
            </div>
          </div>
        </div>
      )}

      {errorMessage && (
        <div className="alert alert-danger" style={{ marginBottom: '16px' }}>
          <AlertTriangle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {/* Affected Road Segment */}
        <div className="input-group" style={{ margin: 0 }}>
          <label className="input-label" htmlFor="segment-select">Affected Road Segment *</label>
          <select
            id="segment-select"
            className="input-select"
            value={segmentId}
            onChange={(e) => setSegmentId(e.target.value)}
          >
            {segments.map((seg) => (
              <option key={seg.id} value={seg.id}>
                {seg.name} ({seg.id} - {seg.functional_class})
              </option>
            ))}
          </select>
        </div>

        {/* Type & Severity in 2 Columns */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <div className="input-group" style={{ margin: 0 }}>
            <label className="input-label" htmlFor="type-select">Incident Type *</label>
            <select
              id="type-select"
              className="input-select"
              value={incidentType}
              onChange={(e) => setIncidentType(e.target.value)}
            >
              <option value="accident">Accident / Collision</option>
              <option value="hazard">Roadway Hazard / Debris</option>
              <option value="roadwork">Construction / Roadwork</option>
              <option value="weather">Weather Obstruction / Flooding</option>
              <option value="stall">Disabled Vehicle / Stall</option>
            </select>
          </div>

          <div className="input-group" style={{ margin: 0 }}>
            <label className="input-label" htmlFor="severity-select">Severity Level *</label>
            <select
              id="severity-select"
              className="input-select"
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
            >
              <option value="low">Low (Minor shoulder slowdown)</option>
              <option value="medium">Medium (Single lane restriction)</option>
              <option value="high">High (Major corridor blockage)</option>
              <option value="critical">Critical (Full road closure)</option>
            </select>
          </div>
        </div>

        {/* Description */}
        <div className="input-group" style={{ margin: 0 }}>
          <label className="input-label" htmlFor="desc-input">Incident Description *</label>
          <textarea
            id="desc-input"
            className="input-textarea"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe what occurred, lane blockage, emergency services, or hazards..."
          />
        </div>

        {/* File Evidence Upload */}
        <div className="input-group" style={{ margin: 0 }}>
          <label className="input-label" htmlFor="file-input">Scene Evidence or Photo (Optional)</label>
          <div
            style={{
              border: '2px dashed var(--border-medium)',
              borderRadius: 'var(--radius-md)',
              padding: '16px',
              textAlign: 'center',
              background: 'var(--bg-surface-subtle)',
              cursor: 'pointer',
            }}
            onClick={() => document.getElementById('file-input')?.click()}
          >
            <Upload size={24} style={{ margin: '0 auto 8px', color: 'var(--text-muted)' }} />
            <div style={{ fontSize: '13px', fontWeight: 600 }}>
              {selectedFile ? selectedFile.name : 'Click to select photo or evidence document'}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
              JPEG, PNG, or PDF evidence files supported
            </div>
            <input
              id="file-input"
              type="file"
              style={{ display: 'none' }}
              accept="image/*,application/pdf"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setSelectedFile(e.target.files[0]);
                }
              }}
            />
          </div>
          {selectedFile && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', marginTop: '6px' }}>
              <FileText size={14} color="var(--primary-500)" />
              <span>{selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)</span>
              <button
                type="button"
                className="btn btn-ghost"
                style={{ padding: '2px 6px', fontSize: '11px', color: 'var(--status-red)' }}
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedFile(null);
                }}
              >
                Remove
              </button>
            </div>
          )}
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          disabled={submitting}
          style={{ padding: '10px 16px', fontWeight: 600, marginTop: '6px' }}
        >
          <Send size={16} />
          <span>{submitting ? 'Submitting to Backend...' : 'Submit Incident Report'}</span>
        </button>
      </form>
    </div>
  );
};
