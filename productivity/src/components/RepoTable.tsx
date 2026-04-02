import { motion } from 'framer-motion';
import type { RepoAggregate } from '../types';
import { currency, numberFmt } from '../utils';

interface Props {
  repos: RepoAggregate[];
  selectedRepo: string | null;
  onSelect: (repo: string) => void;
}

export default function RepoTable({ repos, selectedRepo, onSelect }: Props) {
  return (
    <div className="table-shell">
      <table className="repo-table">
        <thead>
          <tr>
            <th>Repository</th>
            <th>Matched Runs</th>
            <th>Avg Cost Saved</th>
            <th>Avg Time Saved</th>
            <th>Avg AI Resolution</th>
            <th>Efficiency</th>
          </tr>
        </thead>
        <tbody>
          {repos.map((repo, index) => (
            <motion.tr
              key={repo.repo}
              className={selectedRepo === repo.repo ? 'selected-row' : ''}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.04 }}
              onClick={() => onSelect(repo.repo)}
            >
              <td>{repo.repo}</td>
              <td>{repo.runs}</td>
              <td>{currency.format(repo.avgCostSaved)}</td>
              <td>{numberFmt.format(repo.avgTimeSaved)} min</td>
              <td>{numberFmt.format(repo.avgAiMinutes)} min</td>
              <td>{numberFmt.format(repo.efficiencyPercent)}%</td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
