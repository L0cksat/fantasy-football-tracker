import { Routes } from '@angular/router';
import { DashboardComponent } from './components/dashboard/dashboard';
import { HomeComponent } from './components/home/home';

export const routes: Routes = [
  { path: '', component: HomeComponent },
  { path: 'leagues', component: DashboardComponent },
  { path: '**', redirectTo: '' },
];
