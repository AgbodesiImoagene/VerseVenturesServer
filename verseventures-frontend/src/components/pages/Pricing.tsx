import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { publicAPI } from '../../services/api';
import { PricingPlan } from '../../types';
import { CheckIcon } from '@heroicons/react/24/outline';

const Pricing: React.FC = () => {
  const { user } = useAuth();
  const [plans, setPlans] = useState<PricingPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [billingInterval, setBillingInterval] = useState<'month' | 'year'>('month');

  useEffect(() => {
    const fetchPlans = async () => {
      try {
        const plansData = await publicAPI.getPricingPlans();
        setPlans(plansData);
      } catch (error) {
        console.error('Error fetching pricing plans:', error);
        // Fallback plans if API fails
        setPlans([
          {
            id: 'basic',
            name: 'Basic',
            price: billingInterval === 'month' ? 9 : 90,
            interval: billingInterval,
            features: [
              '1,000 API requests per month',
              'Basic semantic search',
              'Email support',
              'Standard response times',
            ],
          },
          {
            id: 'pro',
            name: 'Pro',
            price: billingInterval === 'month' ? 29 : 290,
            interval: billingInterval,
            features: [
              '10,000 API requests per month',
              'Advanced semantic search',
              'Real-time transcription',
              'Priority support',
              'Faster response times',
              'Custom API keys',
            ],
            popular: true,
          },
          {
            id: 'enterprise',
            name: 'Enterprise',
            price: billingInterval === 'month' ? 99 : 990,
            interval: billingInterval,
            features: [
              'Unlimited API requests',
              'Advanced semantic search',
              'Real-time transcription',
              'Dedicated support',
              'Fastest response times',
              'Custom API keys',
              'Usage analytics',
              'Custom integrations',
            ],
          },
        ]);
      } finally {
        setLoading(false);
      }
    };

    fetchPlans();
  }, [billingInterval]);

  const handleSubscribe = async (planId: string) => {
    if (!user) {
      // Redirect to login with return URL
      window.location.href = `/login?redirect=${encodeURIComponent('/pricing')}`;
      return;
    }

    try {
      const response = await fetch('/api/subscriptions/create-checkout-session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        },
        body: JSON.stringify({
          plan_type: planId,
          interval: billingInterval,
        }),
      });

      const data = await response.json();
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      }
    } catch (error) {
      console.error('Error creating checkout session:', error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="bg-gray-50 py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto max-w-4xl text-center">
          <h1 className="text-base font-semibold leading-7 text-primary-600">Pricing</h1>
          <p className="mt-2 text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl">
            Choose the right plan for your needs
          </p>
        </div>
        <p className="mx-auto mt-6 max-w-2xl text-center text-lg leading-8 text-gray-600">
          Start with our free tier and scale up as your needs grow. All plans include our core semantic search features.
        </p>

        {/* Billing Toggle */}
        <div className="mt-16 flex justify-center">
          <div className="relative bg-white p-1 rounded-lg shadow-sm border border-gray-200">
            <button
              onClick={() => setBillingInterval('month')}
              className={`relative py-2 px-4 text-sm font-medium rounded-md transition-colors ${
                billingInterval === 'month'
                  ? 'bg-primary-600 text-white shadow-sm'
                  : 'text-gray-700 hover:text-gray-900'
              }`}
            >
              Monthly billing
            </button>
            <button
              onClick={() => setBillingInterval('year')}
              className={`relative py-2 px-4 text-sm font-medium rounded-md transition-colors ${
                billingInterval === 'year'
                  ? 'bg-primary-600 text-white shadow-sm'
                  : 'text-gray-700 hover:text-gray-900'
              }`}
            >
              Annual billing
              <span className="ml-1 text-xs text-primary-200">Save 20%</span>
            </button>
          </div>
        </div>

        {/* Pricing Cards */}
        <div className="mt-16 grid max-w-lg grid-cols-1 gap-y-6 sm:mt-20 sm:max-w-none sm:grid-cols-3 sm:gap-x-6 lg:gap-x-8">
          {plans.map((plan) => (
            <div
              key={plan.id}
              className={`relative flex flex-col rounded-3xl bg-white p-8 shadow-sm ring-1 ring-gray-200 ${
                plan.popular ? 'ring-primary-600' : ''
              }`}
            >
              {plan.popular && (
                <div className="absolute -top-5 left-0 right-0 mx-auto w-32 rounded-full bg-gradient-to-r from-primary-600 to-primary-400 py-2 px-3 text-sm font-medium text-white text-center">
                  Most popular
                </div>
              )}
              <div className="mb-8">
                <h3 className="text-lg font-semibold leading-8 text-gray-900">{plan.name}</h3>
                <p className="mt-4 text-sm leading-6 text-gray-600">
                  Perfect for {plan.name.toLowerCase()} users who need reliable semantic search capabilities.
                </p>
                <p className="mt-6 flex items-baseline gap-x-1">
                  <span className="text-4xl font-bold tracking-tight text-gray-900">${plan.price}</span>
                  <span className="text-sm font-semibold leading-6 text-gray-600">
                    /{billingInterval}
                  </span>
                </p>
              </div>
              <ul role="list" className="mb-8 flex flex-1 flex-col gap-y-4">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex gap-x-3">
                    <CheckIcon className="h-6 w-5 flex-none text-primary-600" aria-hidden="true" />
                    <span className="text-sm leading-6 text-gray-600">{feature}</span>
                  </li>
                ))}
              </ul>
              <button
                onClick={() => handleSubscribe(plan.id)}
                className={`w-full rounded-lg px-3 py-2 text-center text-sm font-semibold shadow-sm transition-colors ${
                  plan.popular
                    ? 'bg-primary-600 text-white hover:bg-primary-500'
                    : 'bg-white text-primary-600 ring-1 ring-inset ring-primary-600 hover:bg-primary-50'
                }`}
              >
                {user ? 'Subscribe now' : 'Get started'}
              </button>
            </div>
          ))}
        </div>

        {/* FAQ Section */}
        <div className="mt-32">
          <div className="mx-auto max-w-4xl divide-y divide-gray-900/10">
            <h2 className="text-2xl font-bold leading-10 tracking-tight text-gray-900">
              Frequently asked questions
            </h2>
            <dl className="mt-10 space-y-6 divide-y divide-gray-900/10">
              <div className="pt-6">
                <dt className="text-lg font-semibold leading-7 text-gray-900">
                  Can I change my plan at any time?
                </dt>
                <dd className="mt-2 text-base leading-7 text-gray-600">
                  Yes, you can upgrade or downgrade your plan at any time. Changes will be prorated and reflected in your next billing cycle.
                </dd>
              </div>
              <div className="pt-6">
                <dt className="text-lg font-semibold leading-7 text-gray-900">
                  What happens if I exceed my API request limit?
                </dt>
                <dd className="mt-2 text-base leading-7 text-gray-600">
                  If you exceed your monthly API request limit, your requests will be temporarily blocked until your next billing cycle. You can upgrade your plan to get a higher limit.
                </dd>
              </div>
              <div className="pt-6">
                <dt className="text-lg font-semibold leading-7 text-gray-900">
                  Do you offer refunds?
                </dt>
                <dd className="mt-2 text-base leading-7 text-gray-600">
                  We offer a 30-day money-back guarantee for all paid plans. If you're not satisfied, contact our support team for a full refund.
                </dd>
              </div>
              <div className="pt-6">
                <dt className="text-lg font-semibold leading-7 text-gray-900">
                  Is there a free trial?
                </dt>
                <dd className="mt-2 text-base leading-7 text-gray-600">
                  Yes, all paid plans come with a 14-day free trial. No credit card required to start your trial.
                </dd>
              </div>
            </dl>
          </div>
        </div>

        {/* CTA Section */}
        <div className="mt-32 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
            Ready to get started?
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-gray-600">
            Join thousands of users who are already using VerseVentures for their biblical research needs.
          </p>
          <div className="mt-8 flex justify-center gap-x-6">
            <Link
              to="/register"
              className="btn-primary"
            >
              Start free trial
            </Link>
            <Link
              to="/contact"
              className="btn-secondary"
            >
              Contact sales
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Pricing; 