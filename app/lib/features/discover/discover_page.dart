import 'package:flutter/material.dart';
import '../../core/theme/tokens.dart';
import '../../core/widgets/band_badge.dart';
import '../../core/widgets/verified_badge.dart';
import '../../core/widgets/w_button.dart';
import '../../core/widgets/w_card.dart';

class GiverModel {
  final String id;
  final String name;
  final String headline;
  final String college;
  final String status; // active_now, available_today, inactive
  final String? todayWindow;
  final double responseRate;
  final String avgReplyTime;
  final String band;
  final int capacityLeft;

  const GiverModel({
    required this.id,
    required this.name,
    required this.headline,
    required this.college,
    required this.status,
    this.todayWindow,
    required this.responseRate,
    required this.avgReplyTime,
    required this.band,
    required this.capacityLeft,
  });
}

class DiscoverPage extends StatefulWidget {
  const DiscoverPage({super.key});

  @override
  State<DiscoverPage> createState() => _DiscoverPageState();
}

class _DiscoverPageState extends State<DiscoverPage> {
  // Student state
  final String _trustLevel = 'new';
  final int _maxOpenRequests = 3;
  int _openRequestsCount = 3; // Simulating new student at cap
  bool _hasUnratedSession = false;

  final List<GiverModel> _givers = const [
    GiverModel(
      id: 'g1',
      name: 'Priya Sharma',
      headline: 'Staff Software Engineer at Google',
      college: 'VIPS-TC (Class of 2021)',
      status: 'active_now',
      responseRate: 98.0,
      avgReplyTime: '45m',
      band: 'Top Rated',
      capacityLeft: 3,
    ),
    GiverModel(
      id: 'g2',
      name: 'Rohan Verma',
      headline: 'Product Manager at Microsoft',
      college: 'VIPS-TC (Class of 2019)',
      status: 'available_today',
      todayWindow: '8 to 10 pm',
      responseRate: 92.0,
      avgReplyTime: '2h',
      band: 'Trusted',
      capacityLeft: 1,
    ),
  ];

  Color _getStatusColor(String status) {
    switch (status) {
      case 'active_now':
        return AppColors.successGreen;
      case 'available_today':
        return AppColors.amber;
      case 'inactive':
      default:
        return AppColors.slate;
    }
  }

  String _getStatusText(String status, String? todayWindow) {
    switch (status) {
      case 'active_now':
        return 'Active now';
      case 'available_today':
        return todayWindow != null ? 'Available today ($todayWindow)' : 'Available today';
      case 'inactive':
      default:
        return 'Inactive';
    }
  }

  void _handleRequestMentorship(GiverModel giver) {
    if (_hasUnratedSession) {
      showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Row(
            children: [
              Icon(Icons.star_half, color: AppColors.amber),
              SizedBox(width: 8),
              Text('Rating Required'),
            ],
          ),
          content: const Text(
            'Students must rate completed sessions before sending more requests. '
            'Please submit feedback on your previous mentor session to proceed.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Rate Now'),
            ),
          ],
        ),
      );
      return;
    }

    if (_openRequestsCount >= _maxOpenRequests) {
      showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Row(
            children: [
              Icon(Icons.block, color: Color(0xFFDC2626)),
              SizedBox(width: 8),
              Text('Request Limit Reached'),
            ],
          ),
          content: Text(
            'New students may have at most $_maxOpenRequests open requests. '
            'You currently have $_openRequestsCount pending requests. '
            'Please wait for givers to respond or increase your trust level.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Understand'),
            ),
          ],
        ),
      );
      return;
    }

    // Success
    setState(() => _openRequestsCount++);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Mentorship request sent to ${giver.name}!')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('WarmPath Recommendations'),
        backgroundColor: AppColors.white,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          // Trust Level & Limits Info Banner
          Container(
            margin: const EdgeInsets.only(bottom: 16.0),
            padding: const EdgeInsets.all(14.0),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: AppRadii.card,
              border: Border.all(color: AppColors.teal.withOpacity(0.3)),
            ),
            child: Row(
              children: [
                const Icon(Icons.shield_outlined, color: AppColors.teal, size: 24),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Trust Level: ${_trustLevel.toUpperCase()} • Open Requests: $_openRequestsCount/$_maxOpenRequests',
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                          color: AppColors.deepIndigo,
                        ),
                      ),
                      const SizedBox(height: 2),
                      const Text(
                        'New students have at most 3 open requests. Limits increase as trust grows.',
                        style: TextStyle(fontSize: 12, color: AppColors.slate),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // Givers List
          ..._givers.map(
            (giver) => Padding(
              padding: const EdgeInsets.only(bottom: 16.0),
              child: WCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Top row: verified + band + status colored dot
                    Row(
                      children: [
                        const VerifiedBadge(role: 'Alumnus'),
                        const SizedBox(width: 8),
                        BandBadge(band: giver.band),
                        const Spacer(),
                        // Status colored dot + label
                        Row(
                          children: [
                            Container(
                              width: 9,
                              height: 9,
                              decoration: BoxDecoration(
                                color: _getStatusColor(giver.status),
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 6),
                            Text(
                              _getStatusText(giver.status, giver.todayWindow),
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: _getStatusColor(giver.status),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),

                    Text(
                      giver.name,
                      style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: AppColors.textDark),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      giver.headline,
                      style: const TextStyle(fontSize: 13, color: AppColors.slate),
                    ),
                    Text(
                      giver.college,
                      style: const TextStyle(fontSize: 12, color: AppColors.deepIndigo, fontWeight: FontWeight.w500),
                    ),
                    const SizedBox(height: 12),

                    // Metrics row: response rate & avg reply time from real request history
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                      decoration: BoxDecoration(
                        color: AppColors.surface,
                        borderRadius: AppRadii.badge,
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.bolt, size: 14, color: AppColors.teal),
                          const SizedBox(width: 4),
                          Text(
                            '${giver.responseRate.toStringAsFixed(0)}% response rate',
                            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.textDark),
                          ),
                          const SizedBox(width: 10),
                          const Text('•', style: TextStyle(color: AppColors.slate)),
                          const SizedBox(width: 10),
                          const Icon(Icons.schedule, size: 14, color: AppColors.slate),
                          const SizedBox(width: 4),
                          Text(
                            'avg reply ${giver.avgReplyTime}',
                            style: const TextStyle(fontSize: 12, color: AppColors.slate),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),

                    // Connect button
                    WButton(
                      text: 'Request Mentorship (${giver.capacityLeft} slots left)',
                      onPressed: () => _handleRequestMentorship(giver),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
