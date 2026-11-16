import { useState } from "react";
import {
  Mail,
  Phone,
  Linkedin,
  Github,
  MapPin,
  GraduationCap,
  FolderGit2,
  Award,
  FileCode,
  Copy,
  Check,
  Code2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import type {
  ResumeStructuredContent,
  ResumeExperienceItem,
  ResumeEducationItem,
  ResumeProjectItem,
} from "@/types/resumes";

interface ParsedSectionsViewProps {
  content?: ResumeStructuredContent | null;
  rawText?: string | null;
}

type TabType = "overview" | "skills" | "experience" | "projects-education" | "raw";

export function ParsedSectionsView({ content, rawText }: ParsedSectionsViewProps) {
  const [activeTab, setActiveTab] = useState<TabType>("overview");
  const [copiedRaw, setCopiedRaw] = useState(false);

  const contact = content?.contact_info;
  const summary = content?.summary;
  const skills = content?.skills || [];
  const experience = content?.experience || [];
  const education = content?.education || [];
  const projects = content?.projects || [];
  const certifications = content?.certifications || [];
  const fullRawText = rawText || content?.raw_text || "";

  const handleCopyRaw = () => {
    if (!fullRawText) return;
    navigator.clipboard.writeText(fullRawText);
    setCopiedRaw(true);
    setTimeout(() => setCopiedRaw(false), 2000);
  };

  const renderSummaryText = () => {
    if (!summary) return null;
    if (Array.isArray(summary)) {
      return summary.map((p, idx) => (
        <p key={idx} className="text-sm text-terminal-dark leading-relaxed mb-2 last:mb-0">
          {p}
        </p>
      ));
    }
    return <p className="text-sm text-terminal-dark leading-relaxed">{summary}</p>;
  };

  return (
    <div className="space-y-6">
      {/* Tabs navigation */}
      <div className="flex flex-wrap items-center gap-1 p-1 bg-terminal-warm rounded-card border border-terminal-warmBorder">
        <button
          onClick={() => setActiveTab("overview")}
          className={`px-3.5 py-1.5 rounded-md text-xs font-medium transition-all ${
            activeTab === "overview"
              ? "bg-terminal-warmSurface text-terminal-dark font-semibold shadow-xs border border-terminal-warmBorder"
              : "text-terminal-muted hover:text-terminal-dark"
          }`}
        >
          Overview & Contact
        </button>
        <button
          onClick={() => setActiveTab("skills")}
          className={`px-3.5 py-1.5 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 ${
            activeTab === "skills"
              ? "bg-terminal-warmSurface text-terminal-dark font-semibold shadow-xs border border-terminal-warmBorder"
              : "text-terminal-muted hover:text-terminal-dark"
          }`}
        >
          Skills
          {skills.length > 0 && (
            <span className="font-mono text-[10px] bg-terminal-elevated text-white px-1.5 py-0.2 rounded-full">
              {skills.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab("experience")}
          className={`px-3.5 py-1.5 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 ${
            activeTab === "experience"
              ? "bg-terminal-warmSurface text-terminal-dark font-semibold shadow-xs border border-terminal-warmBorder"
              : "text-terminal-muted hover:text-terminal-dark"
          }`}
        >
          Experience
          {experience.length > 0 && (
            <span className="font-mono text-[10px] bg-terminal-elevated text-white px-1.5 py-0.2 rounded-full">
              {experience.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab("projects-education")}
          className={`px-3.5 py-1.5 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 ${
            activeTab === "projects-education"
              ? "bg-terminal-warmSurface text-terminal-dark font-semibold shadow-xs border border-terminal-warmBorder"
              : "text-terminal-muted hover:text-terminal-dark"
          }`}
        >
          Projects & Education
          {(projects.length > 0 || education.length > 0) && (
            <span className="font-mono text-[10px] bg-terminal-elevated text-white px-1.5 py-0.2 rounded-full">
              {projects.length + education.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab("raw")}
          className={`px-3.5 py-1.5 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 ${
            activeTab === "raw"
              ? "bg-terminal-warmSurface text-terminal-dark font-semibold shadow-xs border border-terminal-warmBorder"
              : "text-terminal-muted hover:text-terminal-dark"
          }`}
        >
          <FileCode className="w-3.5 h-3.5" />
          Raw Text
        </button>
      </div>

      {/* Tab: Overview */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Contact Details Card */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Contact Information</CardTitle>
            </CardHeader>
            <CardContent>
              {contact && Object.values(contact).some(Boolean) ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                  {contact.email && (
                    <div className="flex items-center gap-2 p-2.5 rounded-md bg-terminal-warm/60 border border-terminal-warmBorder">
                      <Mail className="w-4 h-4 text-terminal-primary shrink-0" />
                      <span className="font-mono text-terminal-dark truncate">{contact.email}</span>
                    </div>
                  )}
                  {contact.phone && (
                    <div className="flex items-center gap-2 p-2.5 rounded-md bg-terminal-warm/60 border border-terminal-warmBorder">
                      <Phone className="w-4 h-4 text-terminal-primary shrink-0" />
                      <span className="font-mono text-terminal-dark">{contact.phone}</span>
                    </div>
                  )}
                  {contact.linkedin && (
                    <div className="flex items-center gap-2 p-2.5 rounded-md bg-terminal-warm/60 border border-terminal-warmBorder">
                      <Linkedin className="w-4 h-4 text-[#8DB4FF] shrink-0" />
                      <a
                        href={contact.linkedin.startsWith("http") ? contact.linkedin : `https://${contact.linkedin}`}
                        target="_blank"
                        rel="noreferrer"
                        className="font-mono text-terminal-dark hover:text-terminal-primary truncate"
                      >
                        {contact.linkedin}
                      </a>
                    </div>
                  )}
                  {contact.github && (
                    <div className="flex items-center gap-2 p-2.5 rounded-md bg-terminal-warm/60 border border-terminal-warmBorder">
                      <Github className="w-4 h-4 text-terminal-dark shrink-0" />
                      <a
                        href={contact.github.startsWith("http") ? contact.github : `https://${contact.github}`}
                        target="_blank"
                        rel="noreferrer"
                        className="font-mono text-terminal-dark hover:text-terminal-primary truncate"
                      >
                        {contact.github}
                      </a>
                    </div>
                  )}
                  {contact.location && (
                    <div className="flex items-center gap-2 p-2.5 rounded-md bg-terminal-warm/60 border border-terminal-warmBorder">
                      <MapPin className="w-4 h-4 text-terminal-primary shrink-0" />
                      <span className="text-terminal-dark truncate">{contact.location}</span>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-xs text-terminal-muted italic">
                  No contact metadata explicitly extracted.
                </p>
              )}
            </CardContent>
          </Card>

          {/* Professional Summary Card */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Professional Summary</CardTitle>
            </CardHeader>
            <CardContent>
              {summary ? (
                renderSummaryText()
              ) : (
                <p className="text-xs text-terminal-muted italic">
                  No professional summary section parsed in this resume version.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab: Skills */}
      {activeTab === "skills" && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Parsed Technical Skills ({skills.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {skills.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {skills.map((skill, idx) => (
                  <Badge
                    key={idx}
                    variant="neutral"
                    className="font-mono text-xs px-3 py-1 bg-terminal-warm border-terminal-warmBorder text-terminal-dark"
                  >
                    <Code2 className="w-3 h-3 text-terminal-muted mr-1" />
                    {skill}
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-xs text-terminal-muted italic">
                No distinct technical skills were identified in the parsed document.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Tab: Experience */}
      {activeTab === "experience" && (
        <div className="space-y-4">
          {experience.length > 0 ? (
            experience.map((item, idx) => {
              const isString = typeof item === "string";
              const exp = isString ? null : (item as ResumeExperienceItem);

              return (
                <Card key={idx} className="border-l-4 border-l-terminal-secondary">
                  <CardContent className="p-5">
                    {isString ? (
                      <p className="text-sm text-terminal-dark whitespace-pre-wrap">{item}</p>
                    ) : (
                      <div className="space-y-3">
                        <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1">
                          <h4 className="text-sm font-bold font-display text-terminal-dark">
                            {exp?.role || "Position Title Unspecified"}
                            {exp?.company && (
                              <span className="text-terminal-muted font-normal">
                                {" "}at <span className="font-semibold text-terminal-dark">{exp.company}</span>
                              </span>
                            )}
                          </h4>
                          {(exp?.start_date || exp?.end_date) && (
                            <span className="text-xs font-mono text-terminal-muted">
                              {exp?.start_date || "—"} &ndash; {exp?.end_date || "Present"}
                            </span>
                          )}
                        </div>

                        {exp?.location && (
                          <div className="flex items-center gap-1 text-xs text-terminal-muted">
                            <MapPin className="w-3.5 h-3.5" />
                            <span>{exp.location}</span>
                          </div>
                        )}

                        {exp?.bullet_points && exp.bullet_points.length > 0 && (
                          <ul className="list-disc list-outside pl-4 space-y-1.5 text-xs text-terminal-dark leading-relaxed">
                            {exp.bullet_points.map((bullet, bIdx) => (
                              <li key={bIdx}>{bullet}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })
          ) : (
            <Card>
              <CardContent className="p-8 text-center text-xs text-terminal-muted italic">
                No structured work experience records parsed from this resume.
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Tab: Projects & Education */}
      {activeTab === "projects-education" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Projects Column */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold font-display text-terminal-dark flex items-center gap-2">
              <FolderGit2 className="w-4 h-4 text-terminal-primary" />
              Projects ({projects.length})
            </h3>
            {projects.length > 0 ? (
              projects.map((proj, idx) => {
                const isString = typeof proj === "string";
                const p = isString ? null : (proj as ResumeProjectItem);
                return (
                  <Card key={idx}>
                    <CardContent className="p-4 space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <h4 className="text-xs font-bold text-terminal-dark font-display">
                          {p?.name || (isString ? proj : "Project")}
                        </h4>
                        {p?.link && (
                          <a
                            href={p.link.startsWith("http") ? p.link : `https://${p.link}`}
                            target="_blank"
                            rel="noreferrer"
                            className="text-xs text-terminal-primary hover:underline font-mono"
                          >
                            Link &rarr;
                          </a>
                        )}
                      </div>
                      {p?.description && (
                        <p className="text-xs text-terminal-dark/90 leading-relaxed">
                          {p.description}
                        </p>
                      )}
                      {p?.technologies && p.technologies.length > 0 && (
                        <div className="flex flex-wrap gap-1 pt-1">
                          {p.technologies.map((t, tIdx) => (
                            <span
                              key={tIdx}
                              className="text-[10px] font-mono bg-terminal-warm text-terminal-muted px-2 py-0.5 rounded border border-terminal-warmBorder"
                            >
                              {t}
                            </span>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                );
              })
            ) : (
              <Card>
                <CardContent className="p-6 text-center text-xs text-terminal-muted italic">
                  No projects parsed.
                </CardContent>
              </Card>
            )}
          </div>

          {/* Education & Certifications Column */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold font-display text-terminal-dark flex items-center gap-2">
              <GraduationCap className="w-4 h-4 text-terminal-primary" />
              Education & Certifications
            </h3>

            {/* Education Items */}
            {education.length > 0 ? (
              education.map((edu, idx) => {
                const isString = typeof edu === "string";
                const e = isString ? null : (edu as ResumeEducationItem);
                return (
                  <Card key={idx}>
                    <CardContent className="p-4 space-y-1">
                      <div className="flex items-baseline justify-between gap-2">
                        <h4 className="text-xs font-bold text-terminal-dark font-display">
                          {e?.institution || (isString ? edu : "Institution")}
                        </h4>
                        {e?.graduation_date && (
                          <span className="text-[11px] font-mono text-terminal-muted">
                            {e.graduation_date}
                          </span>
                        )}
                      </div>
                      {(e?.degree || e?.field_of_study) && (
                        <p className="text-xs text-terminal-muted">
                          {e?.degree} {e?.field_of_study ? `in ${e.field_of_study}` : ""}
                        </p>
                      )}
                    </CardContent>
                  </Card>
                );
              })
            ) : (
              <Card>
                <CardContent className="p-4 text-center text-xs text-terminal-muted italic">
                  No formal education entries parsed.
                </CardContent>
              </Card>
            )}

            {/* Certifications if present */}
            {certifications.length > 0 && (
              <Card>
                <CardHeader className="py-3">
                  <CardTitle className="text-xs flex items-center gap-1.5">
                    <Award className="w-3.5 h-3.5 text-terminal-primary" />
                    Certifications
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-4 pt-0">
                  <ul className="list-disc list-inside space-y-1 text-xs text-terminal-dark font-mono">
                    {certifications.map((cert, cIdx) => (
                      <li key={cIdx}>{cert}</li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* Tab: Raw Text */}
      {activeTab === "raw" && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="text-sm">Extracted Raw Text</CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopyRaw}
              disabled={!fullRawText}
            >
              {copiedRaw ? (
                <>
                  <Check className="w-3.5 h-3.5 text-terminal-success" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  Copy Text
                </>
              )}
            </Button>
          </CardHeader>
          <CardContent>
            {fullRawText ? (
              <pre className="p-4 bg-terminal-dark text-terminal-warm rounded-card font-mono text-xs whitespace-pre-wrap overflow-x-auto max-h-[500px] leading-relaxed border border-terminal-secondary">
                {fullRawText}
              </pre>
            ) : (
              <p className="text-xs text-terminal-muted italic">
                No raw text representation available.
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
