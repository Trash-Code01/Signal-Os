import React from 'react';
import Link from 'next/link';
import { redirect } from 'next/navigation';

export default async function CampaignsIndex() {
  // Redirecting the old route directly to the new 4-step wizard for now
  redirect('/campaigns/new');
  
  return null;
}
