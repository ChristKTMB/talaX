import { Routes } from '@angular/router';

const legal = () => import('./features/legal/legal-page').then((m) => m.LegalPage);

export const routes: Routes = [
  { path: '', loadComponent: () => import('./features/home/home').then((m) => m.Home) },
  { path: 'terms', loadComponent: legal, data: { page: 'terms' } },
  { path: 'privacy', loadComponent: legal, data: { page: 'privacy' } },
  { path: '**', redirectTo: '' },
];
