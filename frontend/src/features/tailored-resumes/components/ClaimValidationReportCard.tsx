import { ShieldCheck, ShieldAlert, CheckCircle2, AlertTriangle, XCircle, Wrench, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { ClaimValidationReport } from "@/types/tailored-resumes";

interface ClaimValidationReportCardProps {
  report?: ClaimValidationReport | null;
  error?: string | null;
}

export function ClaimValidationReportCard({ report, error }: ClaimValidationReportCardProps) {
  if (!report && !error) {
    return (
      <Card>
        <CardContent className="p-6 text-center text-xs text-terminal-muted italic">
          No claim validation audit records available.
        </CardContent>
      </Card>
    );
  }

  const isValid = report?.is_valid ?? false;
  const supportedSkills = report?.supported_skills || [];
  const unsupportedSkills = report?.unsupported_skills || [];
  const supportedMetrics = report?.supported_metrics || [];
  const repairedClaims = report?.repaired_claims || [];
  const violations = report?.violations_detected || [];

  return (
    <Card className={`border-l-4 ${isValid ? "border-l-terminal-success" : "border-l-terminal-error"}`}>
      <CardHeader className="pb-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className={`w-8 h-8 rounded-card flex items-center justify-center ${
              isValid ? "bg-terminal-success/15 text-terminal-success" : "bg-terminal-error/15 text-terminal-error"
            }`}>
              {isValid ? <ShieldCheck className="w-4 h-4" /> : <ShieldAlert className="w-4 h-4" />}
            </div>
            <div>
              <CardTitle className="text-sm flex items-center gap-2">
                Truthful Claim Validation & Audit Trail
                {isValid ? (
                  <Badge variant="success" withDot>
                    Audit Passed
                  </Badge>
                ) : (
                  <Badge variant="danger" withDot>
                    Validation Flagged
                  </Badge>
                )}
              </CardTitle>
              <CardDescription className="text-xs">
                Zero-hallucination verification against master candidate profile evidence
              </CardDescription>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-1">
        {/* Error message if validation failed */}
        {error && (
          <div className="p-3 bg-terminal-error/10 border border-terminal-error/30 rounded-card flex items-start gap-2 text-xs text-[#8A1F11]">
            <XCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Violations if any */}
        {violations.length > 0 && (
          <div className="p-3 bg-terminal-error/10 border border-terminal-error/30 rounded-card space-y-1.5">
            <span className="text-xs font-bold text-[#8A1F11] flex items-center gap-1.5 font-display">
              <AlertTriangle className="w-3.5 h-3.5" />
              Violations Detected ({violations.length})
            </span>
            <ul className="list-disc list-inside text-xs text-[#8A1F11] space-y-1">
              {violations.map((v, idx) => (
                <li key={idx}>{v}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Repaired claims */}
        {repairedClaims.length > 0 && (
          <div className="p-3 bg-terminal-warning/10 border border-terminal-warning/30 rounded-card space-y-1.5">
            <span className="text-xs font-bold text-[#6E4C00] flex items-center gap-1.5 font-display">
              <Wrench className="w-3.5 h-3.5 text-[#E6B84D]" />
              Repaired Claims ({repairedClaims.length}) &mdash; Auto-sanitized to maintain truthfulness
            </span>
            <ul className="list-disc list-inside text-xs text-terminal-dark space-y-1">
              {repairedClaims.map((claim, idx) => (
                <li key={idx} className="italic text-terminal-dark/90">
                  {claim}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Supported vs Unsupported Skills Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
          {/* Supported Skills */}
          <div className="p-3 bg-terminal-warm/60 rounded-card border border-terminal-warmBorder space-y-2">
            <span className="text-xs font-semibold text-terminal-dark flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-terminal-success" />
              Verified Supported Skills ({supportedSkills.length})
            </span>
            {supportedSkills.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {supportedSkills.map((s, idx) => (
                  <Badge
                    key={idx}
                    variant="success"
                    className="font-mono text-[11px] px-2 py-0.5"
                  >
                    {s}
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-xs text-terminal-muted italic">No specific skills audited.</p>
            )}
          </div>

          {/* Unsupported Skills */}
          <div className="p-3 bg-terminal-warm/60 rounded-card border border-terminal-warmBorder space-y-2">
            <span className="text-xs font-semibold text-terminal-dark flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-terminal-warning" />
              Unsupported / Filtered Skills ({unsupportedSkills.length})
            </span>
            {unsupportedSkills.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {unsupportedSkills.map((s, idx) => (
                  <Badge
                    key={idx}
                    variant="warning"
                    className="font-mono text-[11px] px-2 py-0.5"
                  >
                    {s}
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-xs text-terminal-muted italic">
                Zero unsupported skills detected. 100% evidence verified.
              </p>
            )}
          </div>
        </div>

        {/* Supported Metrics */}
        {supportedMetrics.length > 0 && (
          <div className="p-3 bg-terminal-warm/40 rounded-card border border-terminal-warmBorder space-y-1.5">
            <span className="text-xs font-semibold text-terminal-dark flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-terminal-primary" />
              Verified Quantitative Metrics ({supportedMetrics.length})
            </span>
            <div className="flex flex-wrap gap-2 text-xs font-mono text-terminal-dark">
              {supportedMetrics.map((m, idx) => (
                <span
                  key={idx}
                  className="bg-terminal-warmSurface px-2.5 py-1 rounded border border-terminal-warmBorder text-terminal-dark font-medium"
                >
                  {m}
                </span>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

