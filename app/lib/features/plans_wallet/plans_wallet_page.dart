import 'package:flutter/material.dart';
import '../../core/theme/tokens.dart';
import '../../core/widgets/w_button.dart';
import '../../core/widgets/w_card.dart';

class TransactionItem {
  final String id;
  final String operation; // purchase, hold, release, refund, karma, sponsor_fund, sponsor_claim
  final int amount;
  final String description;
  final String date;

  const TransactionItem({
    required this.id,
    required this.operation,
    required this.amount,
    required this.description,
    required this.date,
  });
}

class PlanItem {
  final String id;
  final String name;
  final int price;
  final int monthlyCredits;
  final String description;
  final List<String> features;
  final bool isPopular;

  const PlanItem({
    required this.id,
    required this.name,
    required this.price,
    required this.monthlyCredits,
    required this.description,
    required this.features,
    this.isPopular = false,
  });
}

class PlansWalletPage extends StatefulWidget {
  const PlansWalletPage({super.key});

  @override
  State<PlansWalletPage> createState() => _PlansWalletPageState();
}

class _PlansWalletPageState extends State<PlansWalletPage> {
  int _availableBalance = 10;
  int _heldBalance = 5;
  int _earnedTotal = 16;
  int _karmaBalance = 4;
  String _activePlan = 'plus';

  final List<PlanItem> _plans = const [
    PlanItem(
      id: 'free',
      name: 'Free Campus',
      price: 0,
      monthlyCredits: 0,
      description: 'Unlimited free same-college alumni mentorship sessions.',
      features: ['Own-college alumni always free', 'Direct in-app messaging', 'Standard booking queue'],
    ),
    PlanItem(
      id: 'plus',
      name: 'Plus Plan',
      price: 299,
      monthlyCredits: 5,
      description: 'Includes 1 cross-college session per month + unlimited campus mentorship.',
      features: ['5 monthly credits', 'Cross-college alumni booking', 'Priority slot matching'],
      isPopular: true,
    ),
    PlanItem(
      id: 'pro',
      name: 'Pro Plan',
      price: 899,
      monthlyCredits: 20,
      description: 'Designed for intensive job search & leadership transition.',
      features: ['20 monthly credits (4 sessions)', 'Top-Rated giver priority', 'Unlimited cross-college bookings'],
    ),
  ];

  final List<TransactionItem> _history = const [
    TransactionItem(
      id: 'tx-001',
      operation: 'release',
      amount: 4,
      description: 'Session earnings (80% payout) from mentee session',
      date: 'Today, 2:30 PM',
    ),
    TransactionItem(
      id: 'tx-002',
      operation: 'karma',
      amount: 1,
      description: 'Karma point earned for same-college free mentorship',
      date: 'Yesterday, 6:00 PM',
    ),
    TransactionItem(
      id: 'tx-003',
      operation: 'hold',
      amount: -5,
      description: 'Held in escrow for cross-college system design review',
      date: '17 Oct 2026',
    ),
    TransactionItem(
      id: 'tx-004',
      operation: 'purchase',
      amount: 5,
      description: 'Plus plan monthly grant (Demo payment ₹299)',
      date: '15 Oct 2026',
    ),
    TransactionItem(
      id: 'tx-005',
      operation: 'refund',
      amount: 5,
      description: 'Escrow refunded: Giver declined due to exam schedule',
      date: '12 Oct 2026',
    ),
  ];

  void _showDemoPaymentDialog(PlanItem plan) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: const RoundedRectangleBorder(borderRadius: AppRadii.card),
        title: Row(
          children: [
            const Icon(Icons.bolt, color: AppColors.primaryAction),
            const SizedBox(width: 8),
            Text('Subscribe: ${plan.name}'),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Price: ₹${plan.price} / month', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 6),
            Text('Includes: ${plan.monthlyCredits} monthly credits'),
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.amber.shade50,
                borderRadius: AppRadii.badge,
                border: Border.all(color: Colors.amber.shade300),
              ),
              child: const Row(
                children: [
                  Icon(Icons.info_outline, color: Colors.amber, size: 18),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Demo payment mode: Simulated checkout via MockPaymentAdapter. No real money charged.',
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primaryAction,
              foregroundColor: AppColors.white,
              shape: const RoundedRectangleBorder(borderRadius: AppRadii.button),
            ),
            onPressed: () {
              Navigator.pop(ctx);
              setState(() {
                _activePlan = plan.id;
                _availableBalance += plan.monthlyCredits;
              });
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('Subscribed to ${plan.name}! Added ${plan.monthlyCredits} credits.'),
                  backgroundColor: AppColors.successGreen,
                ),
              );
            },
            child: const Text('Confirm Demo Payment'),
          ),
        ],
      ),
    );
  }

  void _showSponsorDashboard() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Container(
        height: MediaQuery.of(context).size.height * 0.75,
        decoration: const BoxDecoration(
          color: AppColors.white,
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Sponsor CSR Dashboard', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                IconButton(icon: const Icon(Icons.close), onPressed: () => Navigator.pop(ctx)),
              ],
            ),
            const Text('Institutional & Alumni Endowed Fellowship Pools', style: TextStyle(color: AppColors.slate, fontSize: 13)),
            const SizedBox(height: 16),
            Row(
              children: [
                _buildMetricBox('Funded', '50 Credits', AppColors.deepIndigo),
                const SizedBox(width: 10),
                _buildMetricBox('Allocated', '15 Credits', AppColors.amber),
                const SizedBox(width: 10),
                _buildMetricBox('Remaining', '35 Credits', AppColors.teal),
              ],
            ),
            const SizedBox(height: 20),
            const Text('Recent Sponsored Student Claims', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
            const SizedBox(height: 10),
            Expanded(
              child: ListView(
                children: const [
                  ListTile(
                    leading: CircleAvatar(backgroundColor: AppColors.surface, child: Icon(Icons.school, color: AppColors.deepIndigo)),
                    title: Text('Student from VIPS-TC'),
                    subtitle: Text('Claimed 5 credits • Cross-college Mock Interview'),
                    trailing: Text('Active Escrow', style: TextStyle(color: AppColors.teal, fontWeight: FontWeight.bold, fontSize: 12)),
                  ),
                  ListTile(
                    leading: CircleAvatar(backgroundColor: AppColors.surface, child: Icon(Icons.school, color: AppColors.deepIndigo)),
                    title: Text('Student from Tier-3 Engineering College'),
                    subtitle: Text('Claimed 5 credits • Career Transition Session'),
                    trailing: Text('Completed', style: TextStyle(color: AppColors.successGreen, fontWeight: FontWeight.bold, fontSize: 12)),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetricBox(String title, String value, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: color.withOpacity(0.08),
          borderRadius: AppRadii.card,
          border: Border.all(color: color.withOpacity(0.3)),
        ),
        child: Column(
          children: [
            Text(title, style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600)),
            const SizedBox(height: 4),
            Text(value, style: TextStyle(color: color, fontSize: 14, fontWeight: FontWeight.bold)),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Credits & Wallet', style: TextStyle(fontWeight: FontWeight.bold, color: AppColors.textDark)),
        backgroundColor: AppColors.white,
        elevation: 1,
        actions: [
          IconButton(
            icon: const Icon(Icons.account_balance, color: AppColors.deepIndigo),
            tooltip: 'Sponsor Dashboard',
            onPressed: _showSponsorDashboard,
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 4-Quadrant Wallet Balance Cards
            Row(
              children: [
                Expanded(
                  child: WCard(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Row(
                          children: [
                            Icon(Icons.account_balance_wallet, size: 18, color: AppColors.deepIndigo),
                            SizedBox(width: 6),
                            Text('Available', style: TextStyle(fontSize: 12, color: AppColors.slate, fontWeight: FontWeight.w600)),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text('$_availableBalance', style: const TextStyle(fontSize: 26, fontWeight: FontWeight.bold, color: AppColors.deepIndigo)),
                        const Text('Credits to spend', style: TextStyle(fontSize: 11, color: AppColors.slate)),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: WCard(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Row(
                          children: [
                            Icon(Icons.lock_clock, size: 18, color: AppColors.amber),
                            SizedBox(width: 6),
                            Text('In Escrow', style: TextStyle(fontSize: 12, color: AppColors.slate, fontWeight: FontWeight.w600)),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text('$_heldBalance', style: const TextStyle(fontSize: 26, fontWeight: FontWeight.bold, color: AppColors.amber)),
                        const Text('Held for sessions', style: TextStyle(fontSize: 11, color: AppColors.slate)),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: WCard(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Row(
                          children: [
                            Icon(Icons.trending_up, size: 18, color: AppColors.teal),
                            SizedBox(width: 6),
                            Text('Earned', style: TextStyle(fontSize: 12, color: AppColors.slate, fontWeight: FontWeight.w600)),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text('$_earnedTotal', style: const TextStyle(fontSize: 26, fontWeight: FontWeight.bold, color: AppColors.teal)),
                        const Text('From mentoring (80%)', style: TextStyle(fontSize: 11, color: AppColors.slate)),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: WCard(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Row(
                          children: [
                            Icon(Icons.volunteer_activism, size: 18, color: Colors.purple),
                            SizedBox(width: 6),
                            Text('Karma Score', style: TextStyle(fontSize: 12, color: AppColors.slate, fontWeight: FontWeight.w600)),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text('$_karmaBalance', style: const TextStyle(fontSize: 26, fontWeight: FontWeight.bold, color: Colors.purple)),
                        const Text('Free campus sessions', style: TextStyle(fontSize: 11, color: AppColors.slate)),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Sponsored Seat Banner
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.teal.withOpacity(0.08),
                borderRadius: AppRadii.card,
                border: Border.all(color: AppColors.teal.withOpacity(0.4)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.stars, color: AppColors.teal, size: 28),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Sponsored Seats Available', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: AppColors.textDark)),
                        Text('Funded by Alumni CSR. Eligible students book cross-college sessions for ₹0.', style: TextStyle(fontSize: 12, color: AppColors.slate)),
                      ],
                    ),
                  ),
                  ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.teal,
                      foregroundColor: AppColors.white,
                      shape: const RoundedRectangleBorder(borderRadius: AppRadii.badge),
                    ),
                    onPressed: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Sponsored seat claimed! 5 credits allocated for your next session.')),
                      );
                    },
                    child: const Text('Claim Seat'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Subscription Plans Section
            const Text('Subscription Plans', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.textDark)),
            const SizedBox(height: 4),
            const Text('Own-college alumni are always free. Subscribe for cross-college access.', style: TextStyle(color: AppColors.slate, fontSize: 13)),
            const SizedBox(height: 12),
            SizedBox(
              height: 210,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: _plans.length,
                separatorBuilder: (_, __) => const SizedBox(width: 12),
                itemBuilder: (ctx, index) {
                  final p = _plans[index];
                  final isCurrent = _activePlan == p.id;

                  return Container(
                    width: 250,
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: AppColors.white,
                      borderRadius: AppRadii.card,
                      border: Border.all(
                        color: isCurrent ? AppColors.primaryAction : AppColors.surface,
                        width: isCurrent ? 2 : 1,
                      ),
                      boxShadow: [
                        BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 8, offset: const Offset(0, 4)),
                      ],
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(p.name, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                            if (isCurrent)
                              const Chip(
                                label: Text('Active', style: TextStyle(fontSize: 10, color: AppColors.white, fontWeight: FontWeight.bold)),
                                backgroundColor: AppColors.primaryAction,
                                padding: EdgeInsets.zero,
                              ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text('₹${p.price} / month', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.deepIndigo)),
                        const SizedBox(height: 6),
                        Text(p.description, style: const TextStyle(fontSize: 11, color: AppColors.slate), maxLines: 2, overflow: TextOverflow.ellipsis),
                        const Spacer(),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: isCurrent ? AppColors.surface : AppColors.deepIndigo,
                              foregroundColor: isCurrent ? AppColors.slate : AppColors.white,
                              shape: const RoundedRectangleBorder(borderRadius: AppRadii.badge),
                            ),
                            onPressed: isCurrent ? null : () => _showDemoPaymentDialog(p),
                            child: Text(isCurrent ? 'Current Plan' : 'Select Plan'),
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
            const SizedBox(height: 28),

            // Immutable Credit Ledger History
            const Text('Credit Ledger History', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.textDark)),
            const SizedBox(height: 4),
            const Text('Immutable, double-entry balanced transaction ledger.', style: TextStyle(color: AppColors.slate, fontSize: 13)),
            const SizedBox(height: 12),
            ..._history.map((tx) {
              final isPositive = tx.amount > 0;
              Color txColor;
              IconData txIcon;

              switch (tx.operation) {
                case 'release':
                  txColor = AppColors.teal;
                  txIcon = Icons.payments;
                  break;
                case 'karma':
                  txColor = Colors.purple;
                  txIcon = Icons.volunteer_activism;
                  break;
                case 'hold':
                  txColor = AppColors.amber;
                  txIcon = Icons.lock_clock;
                  break;
                case 'refund':
                  txColor = Colors.blue;
                  txIcon = Icons.replay;
                  break;
                default:
                  txColor = AppColors.successGreen;
                  txIcon = Icons.add_circle;
              }

              return Container(
                margin: const EdgeInsets.only(bottom: 10),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                decoration: BoxDecoration(
                  color: AppColors.white,
                  borderRadius: AppRadii.card,
                  boxShadow: [
                    BoxShadow(color: Colors.black.withOpacity(0.02), blurRadius: 4, offset: const Offset(0, 2)),
                  ],
                ),
                child: Row(
                  children: [
                    CircleAvatar(
                      backgroundColor: txColor.withOpacity(0.12),
                      child: Icon(txIcon, color: txColor, size: 20),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(tx.description, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppColors.textDark)),
                          const SizedBox(height: 2),
                          Text(tx.date, style: const TextStyle(fontSize: 11, color: AppColors.slate)),
                        ],
                      ),
                    ),
                    Text(
                      '${isPositive ? '+' : ''}${tx.amount} ${tx.operation == 'karma' ? 'Karma' : 'Credits'}',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                        color: isPositive ? AppColors.successGreen : Colors.red.shade700,
                      ),
                    ),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }
}
