import type { Schemas } from '@/lib/api-client'

function download(template: Schemas['TemplateOut']) {
  const blob = new Blob([`${template.csv_header}\n`], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${template.source}_template.csv`
  link.click()
  URL.revokeObjectURL(url)
}

/** Header-only CSVs showing the columns each export needs. */
export function TemplateLinks({ templates }: { templates: Schemas['TemplateOut'][] }) {
  return (
    <details className="group">
      <summary className="cursor-pointer list-none text-ember hover:underline">
        Download CSV templates
      </summary>
      <ul className="mt-2 flex gap-4">
        {templates.map((template) => (
          <li key={template.source}>
            <button
              type="button"
              className="text-[13px] text-ember hover:underline"
              onClick={() => download(template)}
            >
              {template.label}
            </button>
          </li>
        ))}
      </ul>
    </details>
  )
}
