import BeingRightVsBeingPaid from './insights/being-right-vs-being-paid.mdx'

export const insights = {
  'being-right-vs-being-paid': {
    component: BeingRightVsBeingPaid,
    frontmatter: {
      title: 'Being Right vs Being Paid',
      description: 'Why accuracy doesn’t equal profitability in betting.',
    },
  },
}

export type InsightSlug = keyof typeof insights