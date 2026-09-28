import { useState } from 'react'
import { Check, Clipboard, Printer } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { reportMarkdown, type Report } from '@/lib/reports'

/** Copy as Markdown and Print, the two things a founder does with the report (UI.md §5.6). */
export function ReportActions({ report }: { report: Report }) {
  const [copied, setCopied] = useState(false)

  async function copy() {
    await navigator.clipboard.writeText(reportMarkdown(report))
    setCopied(true)
    window.setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="flex items-center gap-2 print:hidden">
      <Button variant="ghost" onClick={() => void copy()}>
        {copied ? <Check className="text-verdant" aria-hidden /> : <Clipboard aria-hidden />}
        {copied ? 'Copied' : 'Copy as Markdown'}
      </Button>
      <Button variant="secondary" onClick={() => window.print()}>
        <Printer aria-hidden />
        Print
      </Button>
    </div>
  )
}
